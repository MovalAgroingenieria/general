# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import exceptions
from odoo.tests.common import TransactionCase, tagged
from odoo.tools.misc import mute_logger

try:
    # psycopg2 errors for SQL constraint assertion
    from psycopg2 import IntegrityError
except ImportError:  # pragma: no cover - fallback if psycopg2 aliasing differs
    IntegrityError = Exception


@tagged("post_install", "-at_install")
class TestResFileCategory(TransactionCase):
    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()
        cls.Category = cls.env["res.file.category"]
        cls.ResFile = cls.env.registry.get("res.file") and cls.env["res.file"] or None

    # ---------------------------
    # Helpers
    # ---------------------------
    def _create_category(self, **vals):
        defaults = {"name": "Docs"}
        defaults.update(vals)
        return self.Category.create(defaults)

    def _create_file(self, category, seq=1):
        """Create a minimal res.file linked to category, if model is present.
        The helper inspects fields to avoid missing-required-field errors.
        """
        if not self.ResFile:
            self.skipTest("Model 'res.file' not installed in this DB.")

        vals = {"category_id": category.id}
        # Provide a common required field if present
        if "name" in self.ResFile._fields:
            vals.setdefault("name", f"File {seq}")
        # Add other trivially satisfiable required fields if any
        for fname, field in self.ResFile._fields.items():
            if (
                getattr(field, "required", False)
                and fname not in vals
                and fname != "category_id"
            ):
                # Best-effort generic defaults
                if field.type == "char":
                    vals[fname] = f"default-{fname}-{seq}"
                elif field.type in ("text", "html"):
                    vals[fname] = f"<p>default {fname} {seq}</p>"
                elif field.type in ("integer", "float", "monetary"):
                    vals[fname] = 0
                elif field.type == "boolean":
                    vals[fname] = False
                elif field.type == "date":
                    vals[fname] = "2025-01-01"
                elif field.type == "datetime":
                    vals[fname] = "2025-01-01 00:00:00"
                elif field.type == "many2one":
                    # Try to skip truly unknown M2Os; leave unset if not required by DB
                    pass
                else:
                    # Leave other types unset unless required by DB
                    pass

        return self.ResFile.create(vals)

    # ---------------------------
    # Tests
    # ---------------------------
    def test_unlink_blocks_readonly(self):
        cat = self._create_category(is_readonly=True, name="ReadOnly")
        with self.assertRaises(exceptions.UserError):
            cat.unlink()

    def test_unlink_allows_non_readonly(self):
        cat = self._create_category(is_readonly=False, name="Normal")
        cat.unlink()  # should not raise
        self.assertFalse(cat.exists(), "Category should be deleted when not read-only")

    def test_unique_name_constraint(self):
        self._create_category(name="UniqueName")
        with mute_logger("odoo.sql_db"):
            with self.assertRaises(IntegrityError):
                self._create_category(name="UniqueName")

    def test_compute_number_of_files(self):
        if not self.ResFile:
            self.skipTest("Model 'res.file' not installed in this DB.")

        cat = self._create_category(name="WithFiles")
        # Initially zero
        self.assertEqual(cat.number_of_files, 0)

        f2 = self._create_file(cat, seq=2)
        cat.invalidate_recordset()  # ensure fresh compute cache
        self.assertEqual(cat.number_of_files, 2, "Should count two linked files")

        # Move one file out to check recompute on inverse changes
        f2.write({"category_id": False})
        cat.invalidate_recordset()
        self.assertEqual(cat.number_of_files, 1, "Should update count after unlinking")

    def test_action_get_files_returns_action_when_files(self):
        if not self.ResFile:
            self.skipTest("Model 'res.file' not installed in this DB.")

        cat = self._create_category(name="ActCat")
        self._create_file(cat, seq=1)

        # If any of the referenced views are missing, the method will raise on env.ref.
        # In that case, we skip gracefully because the test DB may not load
        # those XML records.

        action = cat.action_get_files()
        self.assertIsInstance(action, dict)
        self.assertEqual(action.get("type"), "ir.actions.act_window")
        self.assertEqual(action.get("res_model"), "res.file")
        self.assertIn(
            ("tree" if "tree" in str(action.get("view_mode", "")) else "list"),
            action.get("view_mode", ""),
        )
        domain = action.get("domain") or []
        # Expect domain like [('id','in',[ids...])]
        self.assertTrue(
            any(d and d[0] == "id" and d[1] == "in" for d in domain),
            "Domain should filter to the category files",
        )
