# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import unittest

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase

BaseCase = TransactionCase


class TestConfigSettingsFilePrefix(BaseCase):
    """Tests for res.config.settings <-> res.company.file_prefix related field."""

    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()
        cls.Company = cls.env["res.company"]
        cls.Settings = cls.env["res.config.settings"]

        # Current company and an alternate one to check company-dependent behavior
        cls.company_main = cls.env.company
        cls.company_alt = cls.Company.create({"name": "Alt Co FP"})

    # -------------------------
    # Helpers
    # -------------------------

    def _new_settings(self, company):
        """Create a settings wizard bound to a specific company."""
        return self.Settings.with_company(company).create({"company_id": company.id})

    # -------------------------
    # Tests
    # -------------------------

    def test_read_mirrors_company_value(self):
        """Reading file_prefix in settings mirrors the company's value."""
        # Set a value at company level (under the main company context)
        self.Company.with_company(self.company_main).browse(
            self.company_main.id
        ).file_prefix = "MAIN123"
        # Create wizard in that company and read
        wiz = self._new_settings(self.company_main)
        self.assertEqual(wiz.file_prefix, "MAIN123")

    def test_write_propagates_to_company(self):
        """Writing file_prefix via settings updates res.company.file_prefix."""
        wiz = self._new_settings(self.company_main)
        wiz.file_prefix = "CFG987"
        # Read back under the same company context
        self.assertEqual(
            self.Company.with_company(self.company_main)
            .browse(self.company_main.id)
            .file_prefix,
            "CFG987",
        )

    def test_trim_on_write_via_settings(self):
        """Whitespace is trimmed thanks to res.company write override."""
        wiz = self._new_settings(self.company_main)
        wiz.file_prefix = "   QWERTY   "
        self.assertEqual(
            self.Company.with_company(self.company_main)
            .browse(self.company_main.id)
            .file_prefix,
            "QWERTY",
        )

    def test_length_constraint_enforced_via_settings(self):
        """Length > 10 raises ValidationError even when writing via settings."""
        wiz = self._new_settings(self.company_main)
        with self.assertRaises(ValidationError):
            wiz.file_prefix = "ABCDEFGHIJK"  # 11 chars

    def test_company_dependent_isolation(self):
        """Values differ per company for the same logical field."""
        # Set different values per company using their own settings
        wiz_main = self._new_settings(self.company_main)
        wiz_main.file_prefix = "MAINFP"

        wiz_alt = self._new_settings(self.company_alt)
        wiz_alt.file_prefix = "ALTFP"

        # Read back under each company context
        self.assertEqual(
            self.Company.with_company(self.company_main)
            .browse(self.company_main.id)
            .file_prefix,
            "MAINFP",
        )
        self.assertEqual(
            self.Company.with_company(self.company_alt)
            .browse(self.company_alt.id)
            .file_prefix,
            "ALTFP",
        )

    def test_empty_and_none_allowed(self):
        """Empty or None are allowed and should not raise."""
        wiz = self._new_settings(self.company_main)
        wiz.file_prefix = ""  # empty OK
        self.assertEqual(
            self.Company.with_company(self.company_main)
            .browse(self.company_main.id)
            .file_prefix,
            "",
        )

        # Setting None via write API under the right company context
        self.Company.with_company(self.company_main).browse(self.company_main.id).write(
            {"file_prefix": None}
        )
        self.assertFalse(
            bool(
                self.Company.with_company(self.company_main)
                .browse(self.company_main.id)
                .file_prefix
            )
        )

    def test_create_with_value_propagates(self):
        """Creating the wizard with a value propagates through the related field."""
        # Create the wizard in the main company context
        wiz = self.Settings.with_company(self.company_main).create(
            {"company_id": self.company_main.id, "file_prefix": "ONCREATE"}
        )
        self.assertEqual(
            self.Company.with_company(self.company_main)
            .browse(self.company_main.id)
            .file_prefix,
            "ONCREATE",
        )
        # Changing again should still work
        wiz.file_prefix = "AFTER"
        self.assertEqual(
            self.Company.with_company(self.company_main)
            .browse(self.company_main.id)
            .file_prefix,
            "AFTER",
        )


if __name__ == "__main__":
    unittest.main()
