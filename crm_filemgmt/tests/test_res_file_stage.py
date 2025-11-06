# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import unittest
import uuid

from odoo.tests.common import TransactionCase
from odoo.tools.misc import mute_logger
from psycopg2.errors import UniqueViolation

try:
    # pylint: disable=ungrouped-imports
    from odoo.tests.common import SavepointCase as BaseCase
except ImportError:
    BaseCase = TransactionCase

# psycopg2 exception for UNIQUE constraint
try:
    # pylint: disable=ungrouped-imports

    _PG_UNIQUE = UniqueViolation
except ImportError:  # pragma: no cover
    # Fallback for older psycopg2 versions
    from psycopg2 import IntegrityError

    _PG_UNIQUE = IntegrityError


class TestResFileStage(BaseCase):
    """Tests for res.file.stage (Odoo/OCB 18)."""

    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()
        cls.Stage = cls.env["res.file.stage"]
        cls.suffix = uuid.uuid4().hex[:6]

    # -------------------------
    # Create / fields
    # -------------------------

    def test_create_minimal(self):
        st = self.Stage.create({"name": f"Draft [{self.suffix}]", "sequence": 10})
        self.assertTrue(st)

    def test_flags_persist(self):
        st = self.Stage.create(
            {
                "name": f"Closed [{self.suffix}]",
                "sequence": 99,
                "fold": True,
                "is_closing_stage": True,
            }
        )
        self.assertTrue(st.fold and st.is_closing_stage)

    # -------------------------
    # SQL constraints
    # -------------------------

    def test_unique_name_constraint(self):
        name = f"Uniq [{self.suffix}]"
        self.Stage.create({"name": name, "sequence": 10})
        with mute_logger("odoo.sql_db"):
            with self.assertRaises(UniqueViolation):
                self.Stage.create({"name": name, "sequence": 10})

    # -------------------------
    # Ordering
    # -------------------------

    def test_order_by_sequence_then_name(self):
        """Default order is sequence ASC, then name ASC."""
        # Same sequence, different names -> alphabetical
        s1 = self.Stage.create({"name": "Beta", "sequence": 20})
        s2 = self.Stage.create({"name": "Alpha", "sequence": 20})

        # Lower sequence should come before higher sequence regardless of name
        s3 = self.Stage.create({"name": "Zeta", "sequence": 5})
        s4 = self.Stage.create({"name": "Gamma", "sequence": 30})

        recs = self.Stage.search([])  # respects _order = 'sequence, name'
        ids = [r.id for r in recs]

        # s3 (seq 5) before s1/s2 (seq 20)
        self.assertLess(ids.index(s3.id), ids.index(s1.id))
        self.assertLess(ids.index(s3.id), ids.index(s2.id))

        # Between s1 and s2 (same sequence), "Alpha" before "Beta"
        self.assertLess(ids.index(s2.id), ids.index(s1.id))

        # s4 (seq 30) after s1/s2
        self.assertGreater(ids.index(s4.id), ids.index(s1.id))
        self.assertGreater(ids.index(s4.id), ids.index(s2.id))


if __name__ == "__main__":
    unittest.main()
