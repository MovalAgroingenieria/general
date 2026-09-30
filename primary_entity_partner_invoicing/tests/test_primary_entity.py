# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from unittest.mock import patch

from psycopg2 import IntegrityError

from odoo import Command, fields
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestPrimaryEntity(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()
        cls.line_model = cls.env["account.move.line"]
        cls.primary_a, cls.primary_b = cls.env["res.partner"].create(
            [
                {"name": "Primary A", "is_primary_entity": True},
                {"name": "Primary B", "is_primary_entity": True},
            ]
        )
        cls.member = cls.env["res.partner"].create(
            {"name": "Census member", "is_secondary_entity": True}
        )
        cls.census_a, cls.census_b = cls.env["general.entity.census"].create(
            [
                {"primary_partner_id": partner.id, "period_date": "2026-01-01"}
                for partner in (cls.primary_a, cls.primary_b)
            ]
        )
        cls.source_a, cls.source_b = cls.env["general.entity.census.line"].create(
            [
                {"census_id": census.id, "member_partner_id": cls.member.id}
                for census in (cls.census_a, cls.census_b)
            ]
        )
        cls.additional = cls.env["general.entity.census.additional"].create(
            {"census_line_id": cls.source_b.id, "qty": 3.0}
        )

    def _line_values(self, source=False, **extra):
        vals = {
            "name": "Original invoice description",
            "product_id": self.product_a.id,
            "quantity": 1,
            "price_unit": 100,
            "tax_ids": [Command.clear()],
        }
        if source:
            vals.update(
                billable_item_model=source._name,
                billable_item_res_id=source.id,
            )
        vals.update(extra)
        return vals

    def _invoice(self, *line_values, move_type="out_invoice"):
        return self.env["account.move"].create(
            {
                "move_type": move_type,
                "partner_id": self.partner_a.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [Command.create(vals) for vals in line_values],
            }
        )

    def test_customer_vendor_invoices_and_refunds(self):
        for move_type in ("out_invoice", "in_invoice", "out_refund", "in_refund"):
            with self.subTest(move_type=move_type):
                invoice = self._invoice(
                    self._line_values(self.source_a),
                    self._line_values(self.additional),
                    move_type=move_type,
                )
                self.assertEqual(
                    invoice.invoice_line_ids.mapped("primary_entity_id"),
                    self.primary_a | self.primary_b,
                )
                self.assertFalse(
                    (invoice.line_ids - invoice.invoice_line_ids).primary_entity_id
                )
                self.assertTrue(
                    all(
                        line.name == "Original invoice description"
                        for line in invoice.invoice_line_ids
                    )
                )

    def test_direct_line_creation(self):
        invoice = self._invoice()
        lines = self.line_model.create(
            [
                self._line_values(source, move_id=invoice.id)
                for source in (self.source_a, self.additional)
            ]
        )
        self.assertEqual(lines.primary_entity_id, self.primary_a | self.primary_b)

    def test_explicit_values_are_preserved(self):
        invoice = self._invoice(
            self._line_values(self.source_a, primary_entity_id=self.primary_b.id),
            self._line_values(self.source_a, primary_entity_id=False),
        )
        self.assertEqual(invoice.invoice_line_ids[0].primary_entity_id, self.primary_b)
        self.assertFalse(invoice.invoice_line_ids[1].primary_entity_id)

    def test_missing_deleted_and_unsupported_references(self):
        deleted_id = self.additional.id
        self.additional.unlink()
        for move_type in ("out_invoice", "in_invoice"):
            invoice = self._invoice(
                self._line_values(),
                self._line_values(self.partner_a),
                self._line_values(
                    billable_item_model="general.entity.census.line",
                ),
                self._line_values(
                    billable_item_model="general.entity.census.line",
                    billable_item_res_id=2147483647,
                ),
                self._line_values(
                    billable_item_model="general.entity.census.additional",
                    billable_item_res_id=deleted_id,
                ),
                move_type=move_type,
            )
            self.assertFalse(invoice.line_ids.primary_entity_id)
            invoice.action_post()
            self.assertEqual(invoice.state, "posted")
            invoice.button_draft()
            invoice.button_cancel()
            self.assertEqual(invoice.state, "cancel")

    def test_tax_terms_sections_and_notes_stay_empty(self):
        invoice = self._invoice(
            self._line_values(
                self.source_a, tax_ids=[Command.set(self.tax_sale_a.ids)]
            ),
            *[
                {
                    "name": display_type,
                    "display_type": display_type,
                    "billable_item_model": self.source_a._name,
                    "billable_item_res_id": self.source_a.id,
                }
                for display_type in ("line_section", "line_note")
            ],
        )
        self.assertEqual(
            invoice.invoice_line_ids.filtered(
                lambda line: line.display_type == "product"
            ).primary_entity_id,
            self.primary_a,
        )
        self.assertTrue(
            invoice.line_ids.filtered(lambda line: line.display_type == "tax")
        )
        self.assertFalse(
            invoice.line_ids.filtered(
                lambda line: line.display_type != "product"
            ).primary_entity_id
        )
        self.assertTrue(
            all(
                not allowed
                for allowed in invoice.line_ids.filtered(
                    lambda line: line.display_type != "product"
                ).mapped("primary_entity_manual_allowed")
            )
        )
        invoice.action_post()
        self.assertEqual(invoice.state, "posted")

    def test_journal_entries_are_not_enriched(self):
        entry = self.env["account.move"].create(
            {
                "move_type": "entry",
                "line_ids": [
                    Command.create(
                        {
                            "name": "Entry with a source reference",
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                            "credit": 100,
                            "billable_item_model": self.source_a._name,
                            "billable_item_res_id": self.source_a.id,
                        }
                    ),
                    Command.create(
                        {
                            "name": "Counterpart",
                            "account_id": self.company_data[
                                "default_account_expense"
                            ].id,
                            "debit": 100,
                        }
                    ),
                ],
            }
        )
        self.assertFalse(entry.line_ids.primary_entity_id)
        entry.action_post()

    def test_manual_expense_allocation(self):
        entry = self.env["account.move"].create(
            {
                "move_type": "entry",
                "line_ids": [
                    Command.create(
                        {
                            "name": "Community expense",
                            "account_id": self.company_data[
                                "default_account_expense"
                            ].id,
                            "debit": 100,
                        }
                    ),
                    Command.create(
                        {
                            "name": "Receivable counterpart",
                            "account_id": self.company_data[
                                "default_account_receivable"
                            ].id,
                            "credit": 100,
                        }
                    ),
                ],
            }
        )
        expense = entry.line_ids.filtered(lambda line: line.debit)
        counterpart = entry.line_ids - expense
        self.assertTrue(expense.primary_entity_manual_allowed)
        self.assertFalse(counterpart.primary_entity_manual_allowed)
        expense.write({"primary_entity_id": self.primary_a.id})
        self.assertEqual(expense.primary_entity_id, self.primary_a)
        expense.write({"primary_entity_id": self.primary_b.id})
        self.assertEqual(expense.primary_entity_id, self.primary_b)
        expense.write({"primary_entity_id": False})
        self.assertFalse(expense.primary_entity_id)
        with self.assertRaises(UserError):
            counterpart.write({"primary_entity_id": self.primary_a.id})
        expense.write({"primary_entity_id": self.primary_a.id})
        entry.action_post()
        self.assertEqual(entry.state, "posted")
        self.assertEqual(expense.primary_entity_id, self.primary_a)

    def test_manual_vendor_bill_allocation(self):
        bill = self._invoice(self._line_values(), move_type="in_invoice")
        expense = bill.invoice_line_ids
        self.assertTrue(expense.primary_entity_manual_allowed)
        expense.write({"primary_entity_id": self.primary_a.id})
        self.assertEqual(expense.primary_entity_id, self.primary_a)
        self.assertTrue(
            all(
                not allowed
                for allowed in (bill.line_ids - expense).mapped(
                    "primary_entity_manual_allowed"
                )
            )
        )
        bill.action_post()
        self.assertEqual(bill.state, "posted")

    def test_census_source_is_immutable_for_ui_and_api(self):
        invoice = self._invoice(
            self._line_values(self.source_a),
            self._line_values(self.additional),
            self._line_values(),
        )
        census_line, additional_line, manual = invoice.invoice_line_ids
        self.assertFalse(census_line.primary_entity_manual_allowed)
        self.assertFalse(additional_line.primary_entity_manual_allowed)
        self.assertTrue(manual.primary_entity_manual_allowed)
        for sourced in (census_line, additional_line):
            sourced.write({"primary_entity_id": sourced.primary_entity_id.id})
            for value in (
                self.primary_b.id if sourced == census_line else self.primary_a.id,
                False,
            ):
                with self.assertRaises(UserError):
                    sourced.write({"primary_entity_id": value})
        with self.assertRaises(UserError):
            (census_line | manual).write({"primary_entity_id": self.primary_b.id})
        self.assertFalse(manual.primary_entity_id)
        manual.write({"primary_entity_id": self.primary_b.id})
        self.assertEqual(manual.primary_entity_id, self.primary_b)

    def test_adding_source_and_changing_entity_in_same_write_is_rejected(self):
        invoice = self._invoice(self._line_values())
        line = invoice.invoice_line_ids
        with self.assertRaises(UserError):
            line.write(
                {
                    "billable_item_model": self.source_a._name,
                    "billable_item_res_id": self.source_a.id,
                    "primary_entity_id": self.primary_b.id,
                }
            )
        self.assertFalse(line.primary_entity_id)
        self.assertFalse(line.billable_item_res_id)

    def test_source_changes_copy_and_reversal_preserve_history(self):
        for move_type in ("out_invoice", "in_invoice"):
            with self.subTest(move_type=move_type):
                invoice = self._invoice(
                    self._line_values(self.source_a),
                    self._line_values(self.additional),
                    self._line_values(self.source_a, primary_entity_id=False),
                    move_type=move_type,
                )
                historical_ids = [
                    line.primary_entity_id.id for line in invoice.invoice_line_ids
                ]
                # Change both source paths after the invoice has been created.
                self.census_a.primary_partner_id = self.env["res.partner"].create(
                    {"name": "Changed primary", "is_primary_entity": True}
                )
                self.additional.census_line_id = self.source_a
                invoice.action_post()
                duplicate = invoice.copy()
                reversal = invoice._reverse_moves()
                for move in (invoice, duplicate, reversal):
                    self.assertEqual(
                        [line.primary_entity_id.id for line in move.invoice_line_ids],
                        historical_ids,
                    )
                reversal.action_post()
                self.assertEqual(reversal.state, "posted")

    def test_source_read_failure_is_optional(self):
        source_class = type(self.source_a)
        for exception in (AccessError, MissingError):
            with self.subTest(exception=exception), patch.object(
                source_class,
                "search_fetch",
                side_effect=exception("Unavailable source"),
            ):
                invoice = self._invoice(self._line_values(self.source_a))
                self.assertFalse(invoice.invoice_line_ids.primary_entity_id)
                invoice.action_post()

    def test_record_rules_are_respected(self):
        user = self.env["res.users"].create(
            {
                "name": "Census reader",
                "login": "primary_entity_census_reader",
                "company_id": self.env.company.id,
                "company_ids": [Command.set(self.env.companies.ids)],
                "groups_id": [
                    Command.set(
                        self.env.ref(
                            "base_general_entity.group_general_entity_user"
                        ).ids
                    )
                ],
            }
        )
        self.env["ir.rule"].create(
            {
                "name": "Hide one census source",
                "model_id": self.env["ir.model"]._get_id(self.source_a._name),
                "domain_force": repr([("id", "!=", self.source_a.id)]),
            }
        )
        model = self.line_model.with_user(user)
        entities = model._get_primary_entities_from_billable_items(
            {self.source_a._name: {self.source_a.id, self.source_b.id}},
            model._get_primary_entity_source_fields(),
        )
        self.assertNotIn((self.source_a._name, self.source_a.id), entities)
        self.assertEqual(
            entities[(self.source_b._name, self.source_b.id)], self.primary_b.id
        )

    def test_extensible_source_mapping(self):
        child = self.env["res.partner"].create(
            {"name": "Alternative billable source", "parent_id": self.primary_a.id}
        )
        sources = self.line_model._get_primary_entity_source_fields()
        sources["res.partner"] = ("parent_id",)
        with patch.object(
            type(self.line_model),
            "_get_primary_entity_source_fields",
            return_value=sources,
        ):
            invoice = self._invoice(self._line_values(child))
        self.assertEqual(invoice.invoice_line_ids.primary_entity_id, self.primary_a)

    def test_batch_resolves_each_model_once(self):
        source_class = type(self.source_a)
        additional_class = type(self.additional)
        with patch.object(
            source_class,
            "search_fetch",
            autospec=True,
            side_effect=source_class.search_fetch,
        ) as census_fetch, patch.object(
            additional_class,
            "search_fetch",
            autospec=True,
            side_effect=additional_class.search_fetch,
        ) as additional_fetch:
            invoice = self._invoice(
                *[
                    self._line_values(source)
                    for _ in range(20)
                    for source in (self.source_a, self.source_b, self.additional)
                ]
            )
        self.assertEqual(census_fetch.call_count, 1)
        self.assertEqual(additional_fetch.call_count, 1)
        self.assertEqual(len(invoice.invoice_line_ids), 60)
        self.assertTrue(
            all(line.primary_entity_id for line in invoice.invoice_line_ids)
        )

    def test_batch_query_count_does_not_grow_per_source(self):
        members = self.env["res.partner"].create(
            [
                {"name": f"Batch member {index}", "is_secondary_entity": True}
                for index in range(40)
            ]
        )
        census_lines = self.env["general.entity.census.line"].create(
            [
                {"census_id": self.census_a.id, "member_partner_id": member.id}
                for member in members
            ]
        )
        sources = self.env["general.entity.census.additional"].create(
            [{"census_line_id": line.id, "qty": 1} for line in census_lines]
        )
        source_fields = self.line_model._get_primary_entity_source_fields()
        counts = []
        for records in (sources[:1], sources):
            references = {records._name: set(records.ids)}
            self.env.flush_all()
            self.env.invalidate_all()
            before = self.cr.sql_log_count
            entities = self.line_model._get_primary_entities_from_billable_items(
                references, source_fields
            )
            counts.append(self.cr.sql_log_count - before)
            self.assertEqual(len(entities), len(records))
        self.assertLessEqual(counts[1], counts[0] + 2)

    def test_search_group_and_export(self):
        invoice = self._invoice(
            self._line_values(self.source_a), self._line_values(self.additional)
        )
        lines = invoice.invoice_line_ids
        found = self.line_model.search(
            [("id", "in", lines.ids), ("primary_entity_id", "=", self.primary_a.id)]
        )
        self.assertEqual(found, lines[0])
        groups = self.line_model._read_group(
            [("id", "in", lines.ids)], ["primary_entity_id"], ["__count"]
        )
        self.assertEqual(dict(groups), {self.primary_a: 1, self.primary_b: 1})
        exported = lines.export_data(["primary_entity_id/.id"])["datas"]
        self.assertEqual(
            [str(row[0]) for row in exported],
            [str(self.primary_a.id), str(self.primary_b.id)],
        )

    def test_referenced_primary_cannot_be_deleted(self):
        historical = self.env["res.partner"].create(
            {"name": "Historical primary only", "is_primary_entity": True}
        )
        invoice = self._invoice(self._line_values(primary_entity_id=historical.id))
        self.env.flush_all()
        with self.assertRaises((IntegrityError, UserError)), self.cr.savepoint():
            historical.unlink()
        self.assertEqual(invoice.invoice_line_ids.primary_entity_id, historical)

    def test_additional_fallback(self):
        # The current source field is stored related. Simulate a missing stored
        # value to exercise the documented relational fallback without changing
        # the production source model.
        self.env.flush_all()
        self.cr.execute(
            "UPDATE general_entity_census_additional "
            "SET primary_partner_id = NULL WHERE id = %s",
            [self.additional.id],
        )
        self.additional.invalidate_recordset(["primary_partner_id"])
        invoice = self._invoice(self._line_values(self.additional))
        self.assertEqual(invoice.invoice_line_ids.primary_entity_id, self.primary_b)
