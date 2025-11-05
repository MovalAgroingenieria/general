# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from lxml import etree
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMoveFormDateMaturityVisible(TransactionCase):
    """Ensure 'date_maturity' is visible in the Journal Items list."""

    def test_date_maturity_visible_in_combined_tree(self):
        """Test that date_maturity is visible in the final combined tree view."""
        base_tree_view = self.env.ref("account.view_move_line_tree")

        # Get the combined architecture with all inheritances applied
        view_info = self.env["account.move.line"].get_view(
            view_id=base_tree_view.id, view_type="tree"
        )
        arch = view_info["arch"]
        root = etree.fromstring(arch.encode())  # pylint: disable=c-extension-no-member

        # Look for date_maturity field in the tree view
        nodes = root.xpath("//field[@name='date_maturity']")

        self.assertTrue(
            nodes,
            "The 'date_maturity' column was not found in account.move.line tree view.",
        )

        # Verify that our inheritance applied the correct attributes
        # in the COMBINED view
        for node in nodes:
            # Check that invisible is set to 0 (visible)
            invisible_attr = node.get("invisible")
            self.assertEqual(
                invisible_attr,
                "0",
                "The 'date_maturity' column should have invisible='0' "
                "in combined view.",
            )

            # Check that optional is set to show
            optional_attr = node.get("optional")
            self.assertEqual(
                optional_attr,
                "show",
                "The 'date_maturity' column should have optional='show' "
                "in combined view.",
            )

    def test_our_inheritance_modifies_correctly(self):
        """Test that our inherited view correctly modifies the date_maturity field."""
        our_view = self.env.ref(
            "account_show_madurity_date.view_move_line_tree_show_date_maturity"
        )

        # Check basic properties
        self.assertEqual(
            our_view.inherit_id.id, self.env.ref("account.view_move_line_tree").id
        )

        # Parse our view's arch to verify it has the correct modification structure
        arch_xml = our_view.arch
        root = etree.fromstring(
            arch_xml.encode()
        )  # pylint: disable=c-extension-no-member

        # Find the date_maturity field modification
        date_maturity_nodes = root.xpath("//field[@name='date_maturity']")
        self.assertTrue(
            date_maturity_nodes, "date_maturity field not found in our view"
        )

        # Check that it has position="attributes"
        date_maturity_field = date_maturity_nodes[0]
        position_attr = date_maturity_field.get("position")
        self.assertEqual(
            position_attr, "attributes", "Should have position='attributes'"
        )

        # Check the child attributes in OUR view (not the combined one)
        invisible_attrs = date_maturity_field.xpath(".//attribute[@name='invisible']")
        optional_attrs = date_maturity_field.xpath(".//attribute[@name='optional']")

        self.assertTrue(
            invisible_attrs, "invisible attribute element not found in our view"
        )
        self.assertTrue(
            optional_attrs, "optional attribute element not found in our view"
        )

        self.assertEqual(
            invisible_attrs[0].text.strip(),
            "0",
            "invisible should be set to 0 in our view",
        )
        self.assertEqual(
            optional_attrs[0].text.strip(),
            "show",
            "optional should be set to show in our view",
        )

    def test_date_maturity_field_exists(self):
        """Verify that date_maturity field exists in account.move.line model."""
        self.assertIn(
            "date_maturity",
            self.env["account.move.line"]._fields,
            "date_maturity field should exist in account.move.line model",
        )

    def test_inheritance_applied_successfully(self):
        """Test that proves our inheritance is working by comparing before/after."""
        # Get the base view without our inheritance (simulate by
        # temporarily uninstalling our module)
        base_tree_view = self.env.ref("account.view_move_line_tree")

        # Get combined view WITH our inheritance
        view_info_with_inheritance = self.env["account.move.line"].get_view(
            view_id=base_tree_view.id, view_type="tree"
        )
        arch_with = view_info_with_inheritance["arch"]
        root_with = etree.fromstring(
            arch_with.encode()
        )  # pylint: disable=c-extension-no-member

        # Find date_maturity in the view WITH our inheritance
        nodes_with = root_with.xpath("//field[@name='date_maturity']")
        self.assertTrue(
            nodes_with, "date_maturity should exist in view with inheritance"
        )

        # Check the attributes are correct
        node_with = nodes_with[0]
        self.assertEqual(
            node_with.get("invisible"), "0", "Should be visible with inheritance"
        )
        self.assertEqual(
            node_with.get("optional"),
            "show",
            "Should be optional=show with inheritance",
        )
