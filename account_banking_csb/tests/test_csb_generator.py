# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import date

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCSBGenerator(TransactionCase):
    """Functional tests for CSB file generator on account.payment.order (v18)."""

    def setUp(self):  # pylint: disable=invalid-name
        super().setUp()
        self._setup_models()
        self._setup_company_bank()
        self._setup_payment_method()
        self._setup_payment_mode()
        self._setup_payment_order()
        self._setup_beneficiary()

    def _setup_models(self):
        """Initialize all model references."""
        self.partner_obj = self.env["res.partner"]
        self.order_obj = self.env["account.payment.order"]
        self.pay_line_obj = self.env["account.payment.line"]
        self.pay_mode_obj = self.env["account.payment.mode"]
        self.pay_method_obj = self.env["account.payment.method"]
        self.bank_obj = self.env["res.partner.bank"]
        self.journal_obj = self.env["account.journal"]

    def _setup_company_bank(self):
        """Setup company bank account and journal."""
        self.company = self.env.company
        self.company_partner = self.company.partner_id
        self.company_bank = self.bank_obj.create(
            {
                "acc_number": "20770024003102575766",
                "partner_id": self.company_partner.id,
            }
        )

        self.bank_journal = self.journal_obj.search(
            [
                ("type", "=", "bank"),
                ("company_id", "=", self.company.id),
                ("bank_account_id", "=", self.company_bank.id),
            ],
            limit=1,
        )
        if not self.bank_journal:
            self.bank_journal = self.journal_obj.create(
                {
                    "name": "TEST BANK",
                    "code": "TBNK",
                    "type": "bank",
                    "company_id": self.company.id,
                    "bank_account_id": self.company_bank.id,
                }
            )

    def _setup_payment_method(self):
        """Setup payment method."""
        self.method = self.env.ref(
            "account_banking_csb.csb_direct_debit_payments",
            raise_if_not_found=False,
        ) or self.pay_method_obj.create(
            {
                "name": "CSB Direct Debit",
                "code": "csb_direct_debit_payments",
                "active": True,
            }
        )

    def _setup_payment_mode(self):
        """Setup payment mode with all required fields."""
        vals = {
            "name": "CSB Mode",
            "payment_method_id": self.method.id,
            "payment_order_ok": True,
            "group_lines": True,
            "default_payment_mode": "same",
            "default_target_move": "posted",
            "default_date_type": "due",
            "sequence": 10,
            "initiating_party_identifier": "A12345678",
        }

        self._setup_bank_account_link(vals)
        self._setup_show_bank_account(vals)

        self.mode = self.pay_mode_obj.create(vals)

    def _setup_bank_account_link(self, vals):
        """Setup bank account link configuration."""
        if "bank_account_link" not in self.pay_mode_obj._fields:
            return

        selection = self._get_selection_dict(self.pay_mode_obj, "bank_account_link")
        preferred = ["company", "fixed", "partner", "variable", "none"]
        chosen = next((opt for opt in preferred if opt in selection), None)
        if not chosen:
            return

        vals["bank_account_link"] = chosen

        if chosen == "company":
            self._setup_company_bank_link(vals)
        elif chosen == "fixed":
            self._setup_fixed_bank_link(vals)

    def _setup_company_bank_link(self, vals):
        """Setup company bank account link."""
        for field_name in ("company_partner_bank_id", "partner_bank_id"):
            if field_name in self.pay_mode_obj._fields:
                vals[field_name] = self.company_bank.id
                break

    def _setup_fixed_bank_link(self, vals):
        """Setup fixed bank account link."""
        fixed_journal_field = self._find_fixed_journal_field()
        if fixed_journal_field:
            vals[fixed_journal_field] = self.bank_journal.id

        for field_name in ("company_partner_bank_id", "partner_bank_id"):
            if field_name in self.pay_mode_obj._fields:
                vals[field_name] = self.company_bank.id
                break

    def _find_fixed_journal_field(self):
        """Find the fixed journal field in payment mode."""
        for fname, field in self.pay_mode_obj._fields.items():
            if (
                getattr(field, "type", None) == "many2one"
                and getattr(field, "comodel_name", "") == "account.journal"
                and "fixed" in fname
                and "journal" in fname
            ):
                return fname
        return None

    def _setup_show_bank_account(self, vals):
        """Setup show bank account configuration."""
        if "show_bank_account" in self.pay_mode_obj._fields:
            sel_show = self._get_selection_dict(self.pay_mode_obj, "show_bank_account")
            vals["show_bank_account"] = (
                "full"
                if "full" in sel_show
                else (next(iter(sel_show.keys())) if sel_show else False)
            )

    def _setup_payment_order(self):
        """Setup payment order."""
        self.order = self.order_obj.create(
            {
                "name": "PO/TEST/CSB",
                "payment_method_id": self.method.id,
                "payment_mode_id": self.mode.id,
                "company_partner_bank_id": self.company_bank.id,
            }
        )

    def _setup_beneficiary(self):
        """Setup beneficiary partner."""
        self.partner = self.partner_obj.create(
            {
                "name": "Beneficiario de Prueba Ñ",
                "vat": "ESA12345674",
                "street": "C/ Alcalá 1",
                "street2": "Piso 3",
                "zip": "28001",
                "city": "Madrid",
                "country_id": self.env.ref("base.es").id,
            }
        )

    def _get_selection_dict(self, model, field_name):
        """Get selection dict regardless of being list or callable."""
        fld = model._fields.get(field_name)
        if not fld:
            return {}
        sel = fld.selection
        if callable(sel):
            sel = sel(self.env)
        try:
            return dict(sel)
        except (TypeError, ValueError):
            return {}

    # --------------------------- Helpers -------------------------------------

    def _assert_block_len(self, block, label):
        """Each emitted CSB line is 100 chars + CRLF -> length multiple of 102."""
        error_msg = (
            f"{label}: block length must be multiple of 102 (100 + CRLF), "
            f"got {len(block)}"
        )
        self.assertTrue(len(block) % 102 == 0, error_msg)

    def _get_payment_line_fields(self):
        """Determine the correct field names for payment line."""
        pl_fields = self.pay_line_obj._fields
        return {
            "amount": self._get_amount_field(pl_fields),
            "date": self._get_date_field(pl_fields),
            "communication": self._get_communication_field(pl_fields),
        }

    def _get_amount_field(self, pl_fields):
        """Get the correct amount field name."""
        for field_name in ["amount", "amount_currency", "amount_company_currency"]:
            if field_name in pl_fields:
                return field_name
        return None

    def _get_date_field(self, pl_fields):
        """Get the correct date field name."""
        for field_name in ["date", "payment_date", "ml_maturity_date"]:
            if field_name in pl_fields:
                return field_name
        return None

    def _get_communication_field(self, pl_fields):
        """Get the correct communication field name."""
        for field_name in ["communication", "name"]:
            if field_name in pl_fields:
                return field_name
        return None

    # ----------------------------- Tests -------------------------------------

    def test_header_and_totals(self):
        """Test header and totals generation."""
        head = self.order._cabecera_ordenante_68()  # pylint: disable=protected-access
        self._assert_block_len(head, "Cabecera 68")
        self.assertTrue(head.startswith("0359"))

        totals = self.order._total_general_68(  # pylint: disable=protected-access
            total_payments=0, total_amount=0.0
        )
        self._assert_block_len(totals, "Totales 68")
        self.assertTrue(totals.startswith("0859"))

    def test_beneficiary_records_block(self):
        """Test beneficiary records generation."""
        fields = self._get_payment_line_fields()
        vals = {
            "order_id": self.order.id,
            "partner_id": self.partner.id,
        }

        if fields["amount"]:
            vals[fields["amount"]] = 123.45
        if fields["date"]:
            vals[fields["date"]] = date(2025, 1, 31)
        if fields["communication"]:
            vals[fields["communication"]] = "FAC-2025-0001"

        line = self.pay_line_obj.create(vals)

        block = (
            self.order._registro_beneficiario_68(  # pylint: disable=protected-access
                line, num_of_payment=1
            )
        )
        rows = [r for r in block.split("\r\n") if r]
        self.assertEqual(len(rows), 6)

        for idx, row in enumerate(rows, start=1):
            self.assertEqual(len(row), 100, f"Row {idx} must be exactly 100 chars")

        s68 = self.order._start_68()  # pylint: disable=protected-access
        vat12 = self.env["payment.converter.spain"].convert_text(
            (self.partner.vat or "").strip(), 12
        )
        header_prefix = "0659" + s68 + vat12

        self.assertTrue(rows[0].startswith(header_prefix + "010"))
        self.assertTrue(rows[1].startswith(header_prefix + "011"))
        self.assertTrue(rows[2].startswith(header_prefix + "012"))
        self.assertTrue(rows[3].startswith(header_prefix + "013"))
        self.assertTrue(rows[4].startswith(header_prefix + "014"))
        self.assertTrue(rows[5].startswith(header_prefix + "015"))

    def test_generate_payment_file_no_lines(self):
        """Test payment file generation with no lines."""
        content, filename = self.order.generate_payment_file()
        self.assertIsInstance(content, (bytes, bytearray))
        self.assertTrue(filename.endswith(".txt"))
        self.assertIn("PO_TEST_CSB", filename.replace("/", "_"))

    def test_calculate_num_of_payment_control_digit(self):
        """Test payment number calculation with control digit."""
        line = self.pay_line_obj.new({"partner_id": self.partner.id})
        num = self.order._calculate_num_of_payment(  # pylint: disable=protected-access
            line, 42
        )
        self.assertEqual(len(num), 8)
        self.assertTrue(num.startswith("0000042"))
