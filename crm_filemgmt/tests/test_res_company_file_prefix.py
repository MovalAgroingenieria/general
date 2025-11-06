# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import unittest

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase

try:
    from odoo.tests.common import SavepointCase as BaseCase
except ImportError:
    BaseCase = TransactionCase


class TestResCompanyFilePrefix(BaseCase):
    """Tests for company-dependent 'file_prefix' field on res.company."""

    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()
        cls.Company = cls.env["res.company"]

        # Main company and an alternate company to validate company-dependent behavior
        cls.company_main = cls.env.company
        cls.company_alt = cls.Company.create({"name": "Alt Co for Prefix"})

    # -------------------------
    # Tests
    # -------------------------

    def test_create_trims_and_accepts_up_to_10(self):
        c = self.Company.create({"name": "Trim Co", "file_prefix": "  ABC123   "})
        self.assertEqual(c.file_prefix, "ABC123")

        c2 = self.Company.create({"name": "Ten Co", "file_prefix": "1234567890"})
        self.assertEqual(c2.file_prefix, "1234567890")

    def test_create_rejects_over_10(self):
        with self.assertRaises(ValidationError):
            self.Company.create(
                {"name": "Too Long Co", "file_prefix": "ABCDEFGHIJK"}
            )  # 11

    def test_write_trims_and_enforces_length(self):
        c = self.Company.create({"name": "Write Co", "file_prefix": "X"})
        c.write({"file_prefix": "   QWERTY   "})
        self.assertEqual(c.file_prefix, "QWERTY")

        with self.assertRaises(ValidationError):
            c.write({"file_prefix": "01234567890"})  # 11

    def test_company_dependent_value_is_isolated_by_company(self):
        """
        'file_prefix' is company-dependent: the SAME record yields different values
        when accessed with different active companies via with_company(company).
        """
        # Use the SAME company record, but switch the active company on the recordset
        rec_main_ctx = self.Company.with_company(self.company_main).browse(
            self.company_main.id
        )
        rec_alt_ctx = self.Company.with_company(self.company_alt).browse(
            self.company_main.id
        )

        # Write different values through each company context
        rec_main_ctx.file_prefix = "MAIN123"
        rec_alt_ctx.file_prefix = "ALT98765"

        # Read back with matching contexts and confirm isolation
        self.assertEqual(
            self.Company.with_company(self.company_main)
            .browse(self.company_main.id)
            .file_prefix,
            "MAIN123",
        )
        self.assertEqual(
            self.Company.with_company(self.company_alt)
            .browse(self.company_main.id)
            .file_prefix,
            "ALT98765",
        )

    def test_empty_or_none_is_allowed(self):
        c = self.Company.create({"name": "None OK Co"})
        self.assertFalse(bool(c.file_prefix))  # default None/False
        c.write({"file_prefix": ""})
        self.assertEqual(c.file_prefix, "")

    def test_update_same_value_is_noop(self):
        c = self.Company.create({"name": "Noop Co", "file_prefix": "ABC"})
        c.write({"file_prefix": "ABC"})
        self.assertEqual(c.file_prefix, "ABC")


if __name__ == "__main__":
    unittest.main()
