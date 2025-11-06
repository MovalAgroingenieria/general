# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import unittest
import uuid

from odoo.tests.common import TransactionCase
from odoo.tools.misc import mute_logger
from psycopg2 import IntegrityError as Psycopg2IntegrityError

try:
    # pylint: disable=ungrouped-imports
    from odoo.tests.common import SavepointCase as BaseCase
except ImportError:
    BaseCase = TransactionCase


class TestResFiletag(BaseCase):
    """Tests for res.filetag (Odoo/OCB 18)."""

    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()
        cls.Tag = cls.env["res.filetag"]

    # -------------------------
    # Create / defaults
    # -------------------------

    def test_create_minimal_defaults(self):
        t = self.Tag.create({"name": f"Tag {uuid.uuid4().hex[:6]}"})
        self.assertTrue(t)

    def test_required_name(self):
        with mute_logger("odoo.sql_db"):
            with self.assertRaises(Psycopg2IntegrityError):
                self.Tag.create({})

    # -------------------------
    # SQL constraints
    # -------------------------

    def test_unique_name_constraint(self):
        base = f"To Review [{uuid.uuid4().hex[:6]}]"
        self.Tag.create({"name": base})
        with mute_logger("odoo.sql_db"):
            with self.assertRaises(Psycopg2IntegrityError):
                self.Tag.create({"name": base})

    # -------------------------
    # Ordering
    # -------------------------

    def test_default_order_by_name(self):
        """Default ordering should be ascending by name."""
        self.Tag.create({"name": "Zeta"})
        self.Tag.create({"name": "Alpha"})
        self.Tag.create({"name": "Delta"})

        recs = self.Tag.search([])  # respects _order = 'name'
        names = [r.name for r in recs]
        # Check relative order among our inserts (ignoring any pre-existing data)
        idx = {n: names.index(n) for n in ("Alpha", "Delta", "Zeta")}
        self.assertLess(idx["Alpha"], idx["Delta"])
        self.assertLess(idx["Delta"], idx["Zeta"])


if __name__ == "__main__":
    unittest.main()
