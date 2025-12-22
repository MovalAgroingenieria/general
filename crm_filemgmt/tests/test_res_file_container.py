# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import unittest
import uuid

from odoo.tests.common import TransactionCase

try:
    from odoo.tests.common import SavepointCase as BaseCase
except ImportError:
    BaseCase = TransactionCase


def _ensure_file_prefix(env, value="TST"):
    """Seed company field and company-scoped param used by res.file default."""
    env.company.file_prefix = value
    params = env["ir.config_parameter"].sudo()
    params.set_param(f"crm_filemgmt.file_prefix_{env.company.id}", value)
    # harmless fallbacks if legacy code looks them up:
    params.set_param("crm_filemgmt.file_prefix", value)
    params.set_param("res.file.prefix", value)


class TestResFileContainer(BaseCase):
    """Tests for res.file.container model (Odoo/OCB 18)."""

    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()
        cls.Container = cls.env["res.file.container"]
        cls.File = cls.env["res.file"]
        cls.Stage = cls.env["res.file.stage"]
        cls.Cat = cls.env["res.file.category"]
        cls.Att = cls.env["ir.attachment"]
        cls.Location = cls.env["res.file.location"]
        cls.Type = cls.env["res.file.containertype"]

        # Ensure prefix for res.file default code
        _ensure_file_prefix(cls.env, "TST")

        uniq = uuid.uuid4().hex[:6]

        # Reuse-or-create stage/category to avoid UNIQUE(name) collisions
        cls.stage = cls.Stage.search(
            [("name", "=", "Draft")], limit=1
        ) or cls.Stage.create(
            {
                "name": f"Draft [{uniq}]",
                "sequence": 10,
                "fold": False,
                "is_closing_stage": False,
            }
        )
        cls.cat = cls.Cat.search(
            [("name", "=", "Internal")], limit=1
        ) or cls.Cat.create({"name": f"Internal [{uniq}]", "is_readonly": True})

        # Reuse-or-create location/type safely
        cls.location = cls.Location.search(
            [("name", "=", "A1")], limit=1
        ) or cls.Location.create({"name": f"A1[{uniq}]", "description": "Shelf A1"})
        cls.ctype = cls.Type.search([("name", "=", "Box")], limit=1) or cls.Type.create(
            {"name": f"Box[{uniq}]"}
        )

        # Base container (unique name to avoid clashes)
        cls.container = cls.Container.create(
            {
                "name": f"C-001[{uniq}]",
                "description": "Main Container",
                "location_id": cls.location.id,
                "containertype_id": cls.ctype.id,
            }
        )

    # -------------------------
    # Helpers
    # -------------------------

    def _new_file(self, subject="F-Subject"):
        """Create a minimal res.file pointing to current container."""
        return self.File.create(
            {
                "subject": subject,
                "stage_id": self.stage.id,
                "category_id": self.cat.id,
                "container_id": self.container.id,
            }
        )

    # -------------------------
    # Tests
    # -------------------------

    def test_number_of_files_compute_and_store(self):
        """number_of_files should reflect the amount of related files (store=True)."""
        self.assertEqual(self.container.number_of_files, 0)

        f2 = self._new_file("F2")
        self.container.invalidate_recordset()
        self.assertEqual(self.container.number_of_files, 1)

        f2.container_id = False
        self.container.invalidate_recordset()
        self.assertEqual(self.container.number_of_files, 0)

    def test_action_get_files_without_records_returns_false(self):
        """If no files are linked, action_get_files should return False."""
        empty = self.Container.create(
            {
                "name": "C-EMPTY",
                "description": "Empty Container",
                "location_id": self.location.id,
            }
        )
        self.assertFalse(empty.action_get_files())

    def test_action_get_files_with_records(self):
        """Window action must target res.file with correct domain and view_mode."""
        f1 = self._new_file("A")
        f2 = self._new_file("B")

        action = self.container.action_get_files()
        self.assertIsInstance(action, dict)
        self.assertEqual(action.get("type"), "ir.actions.act_window")
        self.assertEqual(action.get("res_model"), "res.file")
        self.assertIn("list", action.get("view_mode", ""))
        self.assertIn("form", action.get("view_mode", ""))

        # Verificar dominio - ADAPTADO para ambas posibilidades
        domain = action.get("domain") or []

        if domain:
            # Caso 1: Dominio por container_id (recomendado)
            if domain[0][0] == "container_id" and domain[0][1] == "=":
                container_id = domain[0][2]
                self.assertEqual(container_id, self.container.id)

                # Verificar que los archivos están en ese contenedor
                files = self.env["res.file"].search(
                    [("container_id", "=", container_id)]
                )
                file_ids = {f1.id, f2.id}
                found_ids = {f.id for f in files}
                self.assertTrue(file_ids.issubset(found_ids))

            # Caso 2: Dominio por lista de IDs (antiguo formato)
            elif domain[0][0] == "id" and domain[0][1] == "in":
                ids_in_domain = set(domain[0][2])
                self.assertTrue({f1.id, f2.id}.issubset(ids_in_domain))

            else:
                self.fail(f"Unexpected domain format: {domain}")
        else:
            # Si no hay dominio, al menos verificar asociación
            self.assertEqual(f1.container_id, self.container)
            self.assertEqual(f2.container_id, self.container)

    def test_action_get_files_with_records(self):
        """Window action must target res.file with correct domain and view_mode."""
        # Crear archivos de prueba
        f1 = self._new_file("File A")
        f2 = self._new_file("File B")

        # Obtener acción
        action = self.container.action_get_files()

        # Validaciones
        self._validate_action_structure(action)
        self._validate_action_domain(action, [f1, f2])
        self._validate_action_context(action)

    def _validate_action_structure(self, action):
        """Validate basic action structure."""
        self.assertIsInstance(action, dict)
        self.assertEqual(action.get("type"), "ir.actions.act_window")
        self.assertEqual(action.get("res_model"), "res.file")
        self.assertIn("list", action.get("view_mode", ""))
        self.assertIn("form", action.get("view_mode", ""))
        self.assertEqual(action.get("target"), "current")

    def _validate_action_domain(self, action, expected_files):
        """Validate action domain includes expected files."""
        domain = action.get("domain", [])

        # El dominio debe filtrar por container_id
        self.assertEqual(len(domain), 1)
        self.assertEqual(domain[0][0], "container_id")
        self.assertEqual(domain[0][1], "=")
        self.assertEqual(domain[0][2], self.container.id)

        # Verificar que los archivos esperados están en el contenedor
        container_files = self.env["res.file"].search(
            [("container_id", "=", self.container.id)]
        )

        expected_ids = {f.id for f in expected_files}
        actual_ids = {f.id for f in container_files}
        self.assertTrue(expected_ids.issubset(actual_ids))
        self.assertEqual(len(container_files), len(expected_files))

    def _validate_action_context(self, action):
        """Validate action context."""
        context = action.get("context", {})
        self.assertEqual(context.get("default_container_id"), self.container.id)
        self.assertEqual(context.get("search_default_container_id"), self.container.id)


if __name__ == "__main__":
    unittest.main()
