# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import unittest

from odoo.tests.common import TransactionCase

try:
    from odoo.tests.common import SavepointCase as BaseCase
except ImportError:
    BaseCase = TransactionCase

# psycopg2 exceptions for SQL constraint checks
try:
    # psycopg2 >= 2.8 exposes granular errors
    from psycopg2.errors import UniqueViolation as PgUniqueViolation

    _PG_ERR = PgUniqueViolation
except ImportError:  # pragma: no cover
    # Fallback to base IntegrityError if needed
    from psycopg2 import IntegrityError as PgIntegrityError

    _PG_ERR = PgIntegrityError


class TestResFileContainerType(BaseCase):
    """Tests for res.file.containertype (Odoo/OCB 18)."""

    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()
        cls.Model = cls.env["res.file.containertype"]

    def test_create_minimal(self):
        """Creating a minimal container type with just 'name' should work."""
        rec = self.Model.create({"name": "Box"})
        self.assertTrue(rec.id)
        self.assertEqual(rec.name, "Box")
        self.assertFalse(rec.description)
        self.assertFalse(rec.notes)

    def test_unique_name_constraint(self):
        """Duplicate 'name' must violate SQL unique constraint."""
        self.Model.create({"name": "Folder"})
        with self.assertRaises(_PG_ERR):
            # same name again -> UNIQUE(name) should fail
            self.Model.create({"name": "Folder"})

    def test_default_order_by_name(self):
        """Default ordering should be by 'name' ascending."""
        self.Model.create({"name": "Crate"})
        self.Model.create({"name": "Archive"})
        self.Model.create({"name": "Zipper"})

        # search() without explicit order must respect _order = 'name'
        recs = self.Model.search([])
        names = [r.name for r in recs]
        # ensure relative order among our three records is alphabetical
        # (other pre-existing records in DB won't break this assertion)
        idx = {n: names.index(n) for n in ["Archive", "Crate", "Zipper"]}
        self.assertLess(idx["Archive"], idx["Crate"])
        self.assertLess(idx["Crate"], idx["Zipper"])


if __name__ == "__main__":
    unittest.main()
