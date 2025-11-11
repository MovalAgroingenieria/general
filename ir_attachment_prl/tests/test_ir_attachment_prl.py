# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestIrAttachmentPRL(TransactionCase):

    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()
        partner_obj = cls.env["res.partner"]

        # Reuse existing partners to avoid DB-level NOT NULL issues on custom columns
        # that may not be mapped in the ORM (e.g., autopost_bills).
        cls.company = cls.env.company.partner_id

        # Try to get any other partner as "worker" (different from company partner).
        worker = partner_obj.search([("id", "!=", cls.company.id)], limit=1)
        if worker:
            cls.worker = worker
        else:
            # Fallback path: create a lightweight contact ONLY if it is safe.
            # Some DBs have a NOT NULL column 'autopost_bills' not mapped in the ORM.
            cr = cls.env.cr
            cr.execute(
                """
                SELECT is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'res_partner'
                  AND column_name = 'autopost_bills'
                """
            )
            autopost_meta = cr.fetchone()
            if autopost_meta:
                # If the column exists, ensure it won't break
                # inserts when ORM doesn't know it.
                # Set a DB-level default and sanitize existing NULLs.
                cr.execute(
                    "ALTER TABLE res_partner ALTER COLUMN autopost_bills "
                    "SET DEFAULT FALSE"
                )
                cr.execute(
                    "UPDATE res_partner SET autopost_bills = FALSE "
                    "WHERE autopost_bills IS NULL"
                )

            # Now it is safe to create a minimal contact
            cls.worker = partner_obj.create(
                {
                    "name": "Test Worker",
                    "type": "contact",
                }
            )

        # "Today" according to Odoo (respects tz and context)
        cls.today = fields.Date.context_today(cls.env.user)
        # Normalize to date if context_today returned a string
        if isinstance(cls.today, str):
            cls.today = fields.Date.from_string(cls.today)

        cls.tomorrow = cls.today + timedelta(days=1)
        cls.yesterday = cls.today - timedelta(days=1)

    # --------- state compute tests ---------
    def test_state_green_when_no_expiration(self):
        attachment = self.env["ir.attachment"].create(
            {
                "name": "no_expiry.txt",
                "datas": "ZHVtbXk=",
                "mimetype": "text/plain",
            }
        )
        self.assertEqual(
            attachment.state, "green", "No expiration date -> state must be 'green'."
        )

    def test_state_red_when_expiration_today(self):
        attachment = self.env["ir.attachment"].create(
            {
                "name": "expire_today.txt",
                "datas": "ZHVtbXk=",
                "mimetype": "text/plain",
                "expiration_date": self.today,
            }
        )
        self.assertEqual(
            attachment.state, "red", "Expires today -> state must be 'red'."
        )

    def test_state_red_when_expiration_past(self):
        attachment = self.env["ir.attachment"].create(
            {
                "name": "expire_yesterday.txt",
                "datas": "ZHVtbXk=",
                "mimetype": "text/plain",
                "expiration_date": self.yesterday,
            }
        )
        self.assertEqual(
            attachment.state, "red", "Expired yesterday -> state must be 'red'."
        )

    def test_state_green_when_expiration_future(self):
        attachment = self.env["ir.attachment"].create(
            {
                "name": "expire_tomorrow.txt",
                "datas": "ZHVtbXk=",
                "mimetype": "text/plain",
                "expiration_date": self.tomorrow,
            }
        )
        self.assertEqual(
            attachment.state, "green", "Expires tomorrow -> state must be 'green'."
        )

    # --------- create() flow tests ---------
    def test_create_non_prl_flows_through(self):
        """No active_model and no default_is_prl -> use super().create()
        without forcing res_model/res_id."""
        attachment_obj = self.env["ir.attachment"]
        attachment = attachment_obj.create(
            {
                "name": "plain.txt",
                "datas": "ZHVtbXk=",
                "mimetype": "text/plain",
                "is_prl": False,
                "document_type": "admin",
            }
        )
        self.assertFalse(attachment.res_model, "Non-PRL: res_model must not be forced.")
        self.assertFalse(attachment.res_id, "Non-PRL: res_id must not be forced.")

    def test_create_account_journal_passthrough(self):
        """active_model=account.journal -> delegate without touching
        res_model/res_id."""
        attachment_obj = self.env["ir.attachment"].with_context(
            active_model="account.journal"
        )
        attachment = attachment_obj.create(
            {
                "name": "journal.pdf",
                "datas": "ZHVtbXk=",
                "mimetype": "application/pdf",
                "is_prl": True,  # even if PRL, it should delegate
                "document_type": "admin",
            }
        )
        self.assertFalse(
            attachment.res_model, "account.journal: must not set res_model."
        )
        self.assertFalse(attachment.res_id, "account.journal: must not set res_id.")

    def test_create_account_analytic_line_clears_res_model_partner(self):
        """active_model=account.analytic.line -> if res_model=res.partner
        came in, it must be removed before create."""
        attachment_obj = self.env["ir.attachment"].with_context(
            active_model="account.analytic.line"
        )
        attachment = attachment_obj.create(
            {
                "name": "analytic.doc",
                "datas": "ZHVtbXk=",
                "mimetype": "application/octet-stream",
                "res_model": "res.partner",  # must be cleared
                "res_id": self.company.id,
            }
        )
        self.assertNotEqual(
            attachment.res_model,
            "res.partner",
            "Must clear res_model=res.partner for analytic line.",
        )
        # We don't check the exact value afterwards; it is enough that it is
        # NOT linked to partner.
        self.assertFalse(
            attachment.res_model,
            "After cleanup, res_model should be empty or different from res.partner.",
        )

    def test_create_prl_worker_links_to_worker_partner(self):
        """PRL with document_type=worker and worker_id -> links to that
        worker (res.partner)."""
        attachment_obj = self.env["ir.attachment"].with_context(default_is_prl=True)
        attachment = attachment_obj.create(
            {
                "name": "dni_worker.pdf",
                "datas": "ZHVtbXk=",
                "mimetype": "application/pdf",
                "is_prl": True,
                "document_type": "worker",
                "worker_id": self.worker.id,
                # contracting_company_id must be ignored because type is 'worker'
                "contracting_company_id": self.company.id,
            }
        )
        self.assertEqual(
            attachment.res_model, "res.partner", "Should link to res.partner (worker)."
        )
        self.assertEqual(attachment.res_id, self.worker.id, "Should link to worker_id.")
        # 'res_name' is computed by Odoo; it must not be forced in create.

    def test_create_prl_non_worker_links_to_company_partner(self):
        """PRL with type other than 'worker' -> links to
        contracting_company_id."""
        attachment_obj = self.env["ir.attachment"].with_context(default_is_prl=True)
        attachment = attachment_obj.create(
            {
                "name": "appcc.pdf",
                "datas": "ZHVtbXk=",
                "mimetype": "application/pdf",
                "is_prl": True,
                "document_type": "appcc",
                "contracting_company_id": self.company.id,
            }
        )
        self.assertEqual(
            attachment.res_model, "res.partner", "Should link to res.partner (company)."
        )
        self.assertEqual(
            attachment.res_id,
            self.company.id,
            "Should link to contracting_company_id.",
        )

    def test_create_prl_without_partner_does_not_force_link(self):
        """If PRL but no partner is available, res_model/res_id must not be
        forced."""
        attachment_obj = self.env["ir.attachment"].with_context(default_is_prl=True)
        attachment = attachment_obj.create(
            {
                "name": "orphan.pdf",
                "datas": "ZHVtbXk=",
                "mimetype": "application/pdf",
                "is_prl": True,
                "document_type": "admin",
                # no worker_id nor contracting_company_id
            }
        )
        self.assertFalse(
            attachment.res_model, "Without partner: res_model must not be forced."
        )
        self.assertFalse(
            attachment.res_id, "Without partner: res_id must not be forced."
        )
