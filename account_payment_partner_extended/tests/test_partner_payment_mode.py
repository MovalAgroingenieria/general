# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPartnerPaymentModeRelated(TransactionCase):
    """Test suite for computed_customer_payment_mode_id related field."""

    def setUp(self):  # pylint: disable=invalid-name
        super().setUp()
        self._setup_models()
        self._setup_company_bank()
        self._setup_payment_method()
        self._setup_payment_mode()
        self._setup_test_partner()

    def _setup_models(self):
        """Initialize all model references."""
        self.partner_obj = self.env["res.partner"]
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
                "acc_number": "ES6620770024003102575766",
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
        self.method = self.pay_method_obj.search(
            [], limit=1
        ) or self.pay_method_obj.create({"name": "Manual", "code": "manual"})

    def _setup_payment_mode(self):
        """Setup payment mode with all required fields.

        Only include fields that exist on the model so tests run with or
        without account_payment_order (payment_order_ok, group_lines, etc.).
        """
        vals = {
            "name": "TEST MODE",
            "payment_method_id": self.method.id,
            "sequence": 10,
        }
        optional = {
            "payment_order_ok": True,
            "group_lines": True,
            "default_payment_mode": "same",
            "default_target_move": "posted",
            "default_date_type": "due",
        }
        for key, value in optional.items():
            if key in self.pay_mode_obj._fields:
                vals[key] = value

        self._setup_show_bank_account(vals)
        self._setup_bank_account_link(vals)

        self.mode = self.pay_mode_obj.create(vals)

    def _setup_show_bank_account(self, vals):
        """Setup show bank account configuration."""
        if "show_bank_account" in self.pay_mode_obj._fields:
            selection = dict(
                self.pay_mode_obj._fields["show_bank_account"].selection or []
            )
            vals["show_bank_account"] = (
                "full" if "full" in selection else (next(iter(selection), False))
            )

    def _setup_bank_account_link(self, vals):
        """Setup bank account link configuration."""
        chosen_link = None
        if "bank_account_link" in self.pay_mode_obj._fields:
            link_selection = dict(
                self.pay_mode_obj._fields["bank_account_link"].selection or []
            )
            chosen_link = self._get_preferred_link(link_selection)
            if chosen_link:
                vals["bank_account_link"] = chosen_link

        if chosen_link == "company":
            self._setup_company_bank_link(vals)
        elif chosen_link == "fixed":
            self._setup_fixed_bank_link(vals)

    def _get_preferred_link(self, link_selection):
        """Get preferred bank account link type."""
        if "company" in link_selection:
            return "company"
        if "fixed" in link_selection:
            return "fixed"
        return next(iter(link_selection), None)

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
                and "fixed" in fname.lower()
                and "journal" in fname.lower()
            ):
                return fname
        return None

    def _setup_test_partner(self):
        """Setup test partner without any payment mode (override company default)."""
        self.partner = self.partner_obj.create({"name": "Partner Test"})
        self.partner.customer_payment_mode_id = False

    # ----------------------------- Tests -------------------------------------

    def test_related_reflects_and_is_stored(self):
        """Ensure related field mirrors the base field and is stored."""
        # Initially both fields should be empty
        self.assertFalse(self.partner.customer_payment_mode_id)
        self.assertFalse(self.partner.computed_customer_payment_mode_id)

        # Assign a payment mode and verify reflection
        self.partner.customer_payment_mode_id = self.mode
        self.assertEqual(
            self.partner.computed_customer_payment_mode_id,
            self.mode,
            "computed_customer_payment_mode_id must mirror customer_payment_mode_id",
        )

        # Verify it is stored (searchable by domain)
        found = self.partner_obj.search(
            [("computed_customer_payment_mode_id", "=", self.mode.id)]
        )
        self.assertIn(
            self.partner,
            found,
            "Related field must be stored to be searchable via domain",
        )

    def test_field_is_readonly(self):
        """Ensure the related field is marked as readonly."""
        field = self.partner_obj._fields.get("computed_customer_payment_mode_id")
        self.assertTrue(
            field.readonly,
            "computed_customer_payment_mode_id should be readonly",
        )
