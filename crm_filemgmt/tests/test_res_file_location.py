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
    from psycopg2.errors import UniqueViolation as PgUniqueViolation  # >=2.8

    _PG_UNIQUE = PgUniqueViolation
except ImportError:  # pragma: no cover
    from psycopg2 import IntegrityError as PgIntegrityError

    _PG_UNIQUE = PgIntegrityError


class TestResFileLocation(BaseCase):
    """Tests for res.file.location model."""

    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()
        cls.Location = cls.env["res.file.location"]
        cls.Container = cls.env["res.file.container"]
        # Minimal related records are created per test as needed

        # Base location for most tests
        cls.loc = cls.Location.create(
            {
                "name": "LOC-A",
                "description": "Zone A",
            }
        )

    # -------------------------
    # Helpers
    # -------------------------

    def _new_container(self, location=None, name="C-001", desc="Main"):
        """Create a minimal res.file.container pointing to a location."""
        location = location or self.loc
        return self.Container.create(
            {
                "name": name,
                "description": desc,
                "location_id": location.id,
            }
        )

    # -------------------------
    # Compute: number_of_containers
    # -------------------------

    def test_number_of_containers_compute_and_store(self):
        """number_of_containers should equal the number of
        related containers (store=True)."""
        # Initially zero
        self.assertEqual(self.loc.number_of_containers, 0)

        # Create two containers
        c2 = self._new_container(name="C-002")
        # Re-read to ensure stored compute is visible
        self.loc.invalidate_recordset()
        self.assertEqual(self.loc.number_of_containers, 1)

        # Move one container to another location -> count decreases
        other = self.Location.create({"name": "LOC-B"})
        c2.location_id = other.id
        self.loc.invalidate_recordset()
        self.assertEqual(self.loc.number_of_containers, 0)

        # Unset the other container's location (should be prevented
        # by required, but for completeness)
        # We keep test focused; do not unset required fields.

    # -------------------------
    # Action: action_get_containers
    # -------------------------

    def test_action_get_containers_returns_false_when_empty(self):
        """If there are no containers, the action should return False."""
        empty_loc = self.Location.create({"name": "LOC-EMPTY"})
        self.assertFalse(empty_loc.action_get_containers())

    def test_action_get_containers_with_records(self):
        """Action should be an ir.actions.act_window to res.file.container
        with proper domain and view_mode."""
        c1 = self._new_container(name="C-100")
        c2 = self._new_container(name="C-200")

        action = self.loc.action_get_containers()
        self.assertIsInstance(action, dict)
        self.assertEqual(action.get("type"), "ir.actions.act_window")
        self.assertEqual(action.get("res_model"), "res.file.container")

        # view_mode must include tree and form
        self.assertIn("list", action.get("view_mode", ""))
        self.assertIn("form", action.get("view_mode", ""))

        # Domain should include both containers of this location
        domain = action.get("domain") or []
        ids_in_domain = set(domain[0][2]) if domain and domain[0][0] == "id" else set()
        self.assertTrue({c1.id, c2.id}.issubset(ids_in_domain))

    # -------------------------
    # SQL constraints
    # -------------------------


if __name__ == "__main__":
    unittest.main()
