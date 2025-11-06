# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import unittest

from odoo.tests import TransactionCase  # Odoo 18: import recomendado

BaseCase = TransactionCase


class TestCrmFileMgmtMenus(BaseCase):
    """Menu structure tests for crm_filemgmt."""

    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()
        cls.Menu = cls.env["ir.ui.menu"].sudo()
        cls.Group = cls.env["res.groups"].sudo()

        # Resolve menu items (skip suite if menus aren't loaded)
        cls.menu_main = cls.env.ref("crm_filemgmt.menu_main", raise_if_not_found=False)
        cls.menu_filemgmt = cls.env.ref(
            "crm_filemgmt.menu_filemgmt", raise_if_not_found=False
        )
        cls.menu_configuration = cls.env.ref(
            "crm_filemgmt.menu_configuration", raise_if_not_found=False
        )
        cls.menu_config_general_data = cls.env.ref(
            "crm_filemgmt.menu_config_general_data", raise_if_not_found=False
        )
        cls.menu_config_labels = cls.env.ref(
            "crm_filemgmt.menu_config_labels", raise_if_not_found=False
        )

        if not all(
            [
                cls.menu_main,
                cls.menu_filemgmt,
                cls.menu_configuration,
                cls.menu_config_general_data,
                cls.menu_config_labels,
            ]
        ):
            raise unittest.SkipTest(
                "Menus not found. Ensure the XML with menus is installed."
            )

        cls.grp_user = cls.env.ref(
            "crm_filemgmt.group_file_user", raise_if_not_found=False
        )

    def test_root_menu_properties(self):
        """Root menu must have name, icon, and the proper security group."""
        m = self.menu_main
        self.assertEqual(m.name, "Files")

        # En Odoo 18 el icono puede almacenarse en web_icon o web_icon_data
        self.assertTrue(
            bool(getattr(m, "web_icon", None) or getattr(m, "web_icon_data", None)),
            "Root app menu should define web_icon or web_icon_data.",
        )

        # Group restriction
        self.assertIsNotNone(self.grp_user, "group_file_user should exist.")
        self.assertIn(
            self.grp_user.id,
            m.groups_id.ids,
            "Root menu must be restricted to group_file_user.",
        )

        # Root should have no parent
        self.assertFalse(m.parent_id, "Root menu should not have a parent.")

    def test_hierarchy_and_sequences(self):
        """Check parent/child relationships and declared sequences."""
        # Direct children of root
        self.assertEqual(self.menu_filemgmt.parent_id.id, self.menu_main.id)
        self.assertEqual(self.menu_configuration.parent_id.id, self.menu_main.id)

        # Sequences
        self.assertEqual(self.menu_filemgmt.sequence, 10)
        self.assertEqual(self.menu_configuration.sequence, 999)

        # Config submenus under Configuration
        self.assertEqual(
            self.menu_config_general_data.parent_id.id, self.menu_configuration.id
        )
        self.assertEqual(
            self.menu_config_labels.parent_id.id, self.menu_configuration.id
        )

        # Submenu sequences
        self.assertEqual(self.menu_config_general_data.sequence, 20)
        self.assertEqual(self.menu_config_labels.sequence, 30)

    def test_uniqueness_under_parents(self):
        """Ensure single menu with given name exists under its parent."""
        # Under root: 'File Management' and 'Configuration'
        children_root = self.Menu.search([("parent_id", "=", self.menu_main.id)])
        names_root = [m.name for m in children_root]
        self.assertEqual(names_root.count("File Management"), 1)
        self.assertEqual(names_root.count("Configuration"), 1)

        # Under Configuration: 'General Data' and 'Tags'
        children_cfg = self.Menu.search(
            [("parent_id", "=", self.menu_configuration.id)]
        )
        names_cfg = [m.name for m in children_cfg]
        self.assertEqual(names_cfg.count("General Data"), 1)
        self.assertEqual(names_cfg.count("Tags"), 1)

    def test_menu_xml_ids_resolve(self):
        """xml_ids should resolve to the same records searched by name & parent."""
        # File Management by name under root
        found = self.Menu.search(
            [("name", "=", "File Management"), ("parent_id", "=", self.menu_main.id)],
            limit=1,
        )
        self.assertEqual(found.id, self.menu_filemgmt.id)

        # Tags under Configuration
        found2 = self.Menu.search(
            [("name", "=", "Tags"), ("parent_id", "=", self.menu_configuration.id)],
            limit=1,
        )
        self.assertEqual(found2.id, self.menu_config_labels.id)


if __name__ == "__main__":
    unittest.main()
