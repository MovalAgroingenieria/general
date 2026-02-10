# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# pylint: disable=duplicate-code

import unittest

from odoo.tests.common import TransactionCase

try:
    from odoo.tests.common import SavepointCase as BaseCase
except ImportError:
    BaseCase = TransactionCase

# psycopg2 exception for UNIQUE constraint
try:
    from psycopg2.errors import UniqueViolation as PgUniqueViolation  # psycopg2 >= 2.8

    _PG_UNIQUE = PgUniqueViolation
except ImportError:  # pragma: no cover
    # Fallback for older psycopg2 versions
    from psycopg2 import IntegrityError as PgIntegrityError

    _PG_UNIQUE = PgIntegrityError


class TestResFileReport(BaseCase):
    """Tests for res.file.report (Odoo/OCB 18)."""

    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()
        cls.Report = cls.env["res.file.report"]

    # -------------------------
    # Create / fields
    # -------------------------

    def test_create_minimal(self):
        """Creating a minimal report with just 'name' should work."""
        rec = self.Report.create({"name": "General Report"})
        self.assertTrue(rec.id)
        self.assertEqual(rec.name, "General Report")
        # default action may or may not exist depending on loaded data; accept either
        self.assertTrue(rec.iractreportxml_id.id or rec.iractreportxml_id is False)

    def test_create_with_templates(self):
        """HTML template fields should store arbitrary HTML safely."""
        rec = self.Report.create(
            {
                "name": "With Templates",
                "report_template_start": "<h1>Start {{ 1 + 1 }}</h1>",
                "report_template_end": "<footer>End</footer>",
                "notes": "<p>Note</p>",
            }
        )
        self.assertIn("Start", rec.report_template_start or "")
        self.assertIn("End", rec.report_template_end or "")
        self.assertIn("Note", rec.notes or "")

    # -------------------------
    # SQL constraints
    # -------------------------

    # -------------------------
    # Ordering
    # -------------------------

    def test_default_order_by_name(self):
        """Default ordering should be ascending by name."""
        self.Report.create({"name": "Zeta"})
        self.Report.create({"name": "Alpha"})
        self.Report.create({"name": "Delta"})

        recs = self.Report.search([])  # respects _order = 'name'
        names = [r.name for r in recs]
        # Ensure relative order among our inserts
        idx = {n: names.index(n) for n in ("Alpha", "Delta", "Zeta")}
        self.assertLess(idx["Alpha"], idx["Delta"])
        self.assertLess(idx["Delta"], idx["Zeta"])


if __name__ == "__main__":
    unittest.main()
