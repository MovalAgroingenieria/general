# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import date
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCSBGenerator(TransactionCase):
    """Functional tests for CSB file generator on account.payment.order (v18)."""

    def setUp(self):
        super().setUp()
        self.Partner = self.env["res.partner"]
        self.Order = self.env["account.payment.order"]
        self.PayLine = self.env["account.payment.line"]
        self.PayMode = self.env["account.payment.mode"]
        self.PayMethod = self.env["account.payment.method"]
        self.Bank = self.env["res.partner.bank"]
        self.Journal = self.env["account.journal"]

        # Company & bank account (required by _cabecera_ordenante_68)
        self.company = self.env.company
        self.company_partner = self.company.partner_id
        self.company_bank = self.Bank.create({
            # ES IBAN; converter will extract CCC internally if needed
            "acc_number": "20770024003102575766",
            "partner_id": self.company_partner.id,
        })

        # Ensure there is a bank journal linked to that bank account (useful for 'fixed' link)
        self.bank_journal = self.Journal.search([
            ("type", "=", "bank"),
            ("company_id", "=", self.company.id),
            ("bank_account_id", "=", self.company_bank.id),
        ], limit=1)
        if not self.bank_journal:
            self.bank_journal = self.Journal.create({
                "name": "TEST BANK",
                "code": "TBNK",        # <= 5 chars
                "type": "bank",
                "company_id": self.company.id,
                "bank_account_id": self.company_bank.id,
            })

        # Payment method: reuse XML record if present; otherwise create it
        self.method = self.env.ref(
            "account_banking_csb.csb_direct_debit_payments",
            raise_if_not_found=False,
        ) or self.PayMethod.create({
            "name": "CSB Direct Debit",
            "code": "csb_direct_debit_payments",
            "active": True,
        })

        # Helper to get selection dict regardless of being list or callable
        def _selection_dict(model, field_name):
            fld = model._fields.get(field_name)
            if not fld:
                return {}
            sel = fld.selection
            if callable(sel):
                sel = sel(self.env)
            try:
                return {k: v for k, v in sel}
            except Exception:
                return {}

        vals = {
            "name": "CSB Mode",
            "payment_method_id": self.method.id,   # required in many branches
            "payment_order_ok": True,
            "group_lines": True,
            "default_payment_mode": "same",
            "default_target_move": "posted",
            "default_date_type": "due",
            "sequence": 10,
            # Used by _start_68 (12 chars after converter)
            "initiating_party_identifier": "A12345678",
        }

        # bank_account_link (NOT NULL in your branch)
        chosen = None
        if "bank_account_link" in self.PayMode._fields:
            selection = _selection_dict(self.PayMode, "bank_account_link")
            # Prefer 'company' to avoid extra constraints; else 'fixed'; else fallback
            preferred = ["company", "fixed", "partner", "variable", "none"]
            chosen = next((opt for opt in preferred if opt in selection), None) or (next(iter(selection.keys())) if selection else None)
            if chosen:
                vals["bank_account_link"] = chosen

        # If the link is 'company' we’re done; if it's 'fixed', set the fixed journal field
        if chosen == "company":
            # Some branches also expose a MODE-level bank account field; set it if present
            for f in ("company_partner_bank_id", "partner_bank_id"):
                if f in self.PayMode._fields:
                    vals[f] = self.company_bank.id
                    break
        elif chosen == "fixed":
            # Find the MODE field that expects an account.journal (usually fixed_journal_id)
            fixed_journal_field = None
            for fname, field in self.PayMode._fields.items():
                if getattr(field, "type", None) == "many2one" and getattr(field, "comodel_name", "") == "account.journal":
                    # prefer names that contain 'fixed' and 'journal'
                    if "fixed" in fname and "journal" in fname:
                        fixed_journal_field = fname
                        break
            if not fixed_journal_field:
                # fallback: any journal M2o on mode
                for fname, field in self.PayMode._fields.items():
                    if getattr(field, "type", None) == "many2one" and getattr(field, "comodel_name", "") == "account.journal":
                        fixed_journal_field = fname
                        break
            if fixed_journal_field:
                vals[fixed_journal_field] = self.bank_journal.id
            # Also set a MODE-level bank account if the branch requires it
            for f in ("company_partner_bank_id", "partner_bank_id"):
                if f in self.PayMode._fields:
                    vals[f] = self.company_bank.id
                    break

        # show_bank_account (some branches keep it)
        if "show_bank_account" in self.PayMode._fields:
            sel_show = _selection_dict(self.PayMode, "show_bank_account")
            vals["show_bank_account"] = "full" if "full" in sel_show else (next(iter(sel_show.keys())) if sel_show else False)

        self.mode = self.PayMode.create(vals)

        # Payment order (uses method + mode + company bank)
        self.order = self.Order.create({
            "name": "PO/TEST/CSB",
            "payment_method_id": self.method.id,
            "payment_mode_id": self.mode.id,
            "company_partner_bank_id": self.company_bank.id,
        })

        # Beneficiary with VAT + address (used in beneficiary records)
        self.partner = self.Partner.create({
            "name": "Beneficiario de Prueba Ñ",
            "vat": "ES12345678",
            "street": "C/ Alcalá 1",
            "street2": "Piso 3",
            "zip": "28001",
            "city": "Madrid",
            "country_id": self.env.ref("base.es").id,
        })

    # --------------------------- Helpers ---------------   ----------------------

    def _assert_block_len(self, block: str, label: str):
        """Each emitted CSB line is 100 chars + CRLF -> length multiple of 102."""
        self.assertTrue(
            len(block) % 102 == 0,
            f"{label}: block length must be multiple of 102 (100 + CRLF), got {len(block)}",
        )

    # ----------------------------- Tests -------------------------------------

    def test_header_and_totals(self):
        head = self.order._cabecera_ordenante_68()
        self._assert_block_len(head, "Cabecera 68")
        self.assertTrue(head.startswith("0359"))

        totals = self.order._total_general_68(total_payments=0, total_amount=0.0)
        self._assert_block_len(totals, "Totales 68")
        self.assertTrue(totals.startswith("0859"))

    def test_beneficiary_records_block(self):
        # Pick the correct amount/date/communication fields for this branch
        pl_fields = self.PayLine._fields

        # amount-like field
        if "amount" in pl_fields:
            amount_key = "amount"
        elif "amount_currency" in pl_fields:
            amount_key = "amount_currency"
        elif "amount_company_currency" in pl_fields:
            amount_key = "amount_company_currency"
        else:
            # Fallback: some branches compute amount from move lines; give a safe default
            amount_key = None

        # date-like field
        if "date" in pl_fields:
            date_key = "date"
        elif "payment_date" in pl_fields:
            date_key = "payment_date"
        elif "ml_maturity_date" in pl_fields:
            date_key = "ml_maturity_date"
        else:
            date_key = None

        # communication-like field
        if "communication" in pl_fields:
            comm_key = "communication"
        elif "name" in pl_fields:
            comm_key = "name"
        else:
            comm_key = None

        vals = {
            "order_id": self.order.id,
            "partner_id": self.partner.id,
        }
        if amount_key:
            vals[amount_key] = 123.45
        if date_key:
            from datetime import date as _d
            vals[date_key] = _d(2025, 1, 31)
        if comm_key:
            vals[comm_key] = "FAC-2025-0001"

        line = self.PayLine.create(vals)

        block = self.order._registro_beneficiario_68(line, num_of_payment=1)
        rows = [r for r in block.split("\r\n") if r]
        self.assertEqual(len(rows), 6)
        for idx, row in enumerate(rows, start=1):
            self.assertEqual(len(row), 100, f"Row {idx} must be exactly 100 chars")

            # Common prefix: 0659 + s68 + VAT(12)
            s68 = self.order._start_68()
            vat12 = self.env["payment.converter.spain"].convert_text(
                (self.partner.vat or "").strip(), 12
            )
            head = "0659" + s68 + vat12

            # Now assert each record type code
            self.assertTrue(rows[0].startswith(head + "010"))  # name
            self.assertTrue(rows[1].startswith(head + "011"))  # street
            self.assertTrue(rows[2].startswith(head + "012"))  # zip short + city
            self.assertTrue(rows[3].startswith(head + "013"))  # zip long + state + country
            self.assertTrue(rows[4].startswith(head + "014"))  # num_of_payment + date + amount
            self.assertTrue(rows[5].startswith(head + "015"))  # refs + gen date + amount + comm

    def test_generate_payment_file_no_lines(self):
        content, fname = self.order.generate_payment_file()
        self.assertIsInstance(content, (bytes, bytearray))
        self.assertTrue(fname.endswith(".txt"))
        self.assertIn("PO_TEST_CSB", fname.replace("/", "_"))

    def test_calculate_num_of_payment_control_digit(self):
        line = self.PayLine.new({"partner_id": self.partner.id})
        num = self.order._calculate_num_of_payment(line, 42)
        self.assertEqual(len(num), 8)
        self.assertTrue(num.startswith("0000042"))
