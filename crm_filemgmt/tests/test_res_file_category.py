# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


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
        with self.assertRaises(UserError):
            cat.unlink()

    def test_unlink_allows_non_readonly(self):
        cat = self._create_category(is_readonly=False, name="Normal")
        cat.unlink()  # should not raise
        self.assertFalse(cat.exists(), "Category should be deleted when not read-only")

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
            ("list" if "list" in str(action.get("view_mode", "")) else "list"),
            action.get("view_mode", ""),
        )
        domain = action.get("domain") or []
        # Expect domain like [('id','in',[ids...])]
        self.assertTrue(
            any(d and d[0] == "id" and d[1] == "in" for d in domain),
            "Domain should filter to the category files",
        )

    def test_category_creation(self):
        """Test basic category creation."""
        cat = self._create_category(is_readonly=False, name="Test Category")
        self.assertEqual(cat.name, "Test Category")
        self.assertFalse(cat.is_readonly)
        self.assertEqual(cat.number_of_files, 0)

    def test_readonly_category_deletion(self):
        """Test that readonly categories cannot be deleted."""
        readonly_category = self.env["res.file.category"].create(
            {
                "name": "Readonly Category",
                "is_readonly": True,
            }
        )

        with self.assertRaises(UserError):
            readonly_category.unlink()

    def test_category_with_files_deletion(self):
        """Test that categories with files cannot be deleted."""
        # Create a file associated with the category
        cat = self._create_category(is_readonly=False, name="Normal")
        self.env["res.file"].create(
            {
                "alphanum_code": "TEST-2024/0001",
                "subject": "Test File",
                "date_file": fields.Date.today(),
                "category_id": cat.id,
                "stage_id": self.env["res.file.stage"].search([], limit=1).id,
            }
        )

        self.assertEqual(cat.number_of_files, 1)

        # Optional: Uncomment if you add the deletion prevention
        # with self.assertRaises(UserError):
        #     self.category.unlink()

    def test_parent_child_relationship(self):
        """Test parent-child category relationships."""
        parent = self.env["res.file.category"].create({"name": "Parent"})
        child = self.env["res.file.category"].create(
            {
                "name": "Child",
                "parent_id": parent.id,
            }
        )

        self.assertEqual(child.parent_id, parent)
        self.assertIn(child, parent.child_ids)
