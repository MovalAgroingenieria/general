# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestAssemblyDelegationManagerUi(AssemblyTestMixin, TransactionCase):
    def test_manager_action_and_menu_xmlids_exist(self):
        self.env.ref("base_assembly.assembly_delegation_action_manager")
        self.env.ref("base_assembly.assembly_delegation_menu")

    def test_manager_action_model_groups_and_views(self):
        act = self.env.ref("base_assembly.assembly_delegation_action_manager")
        self.assertEqual(act.res_model, "assembly.delegation")
        self.assertEqual(act.view_mode, "list,form")
        self.assertIn(
            self.env.ref("base_assembly.assembly_group_manager"),
            act.groups_id,
        )
        self.assertEqual(
            act.search_view_id,
            self.env.ref("base_assembly.assembly_delegation_view_search_manager"),
        )
        list_line = act.view_ids.filtered(lambda v: v.view_mode == "list")
        form_line = act.view_ids.filtered(lambda v: v.view_mode == "form")
        self.assertEqual(len(list_line), 1)
        self.assertEqual(len(form_line), 1)
        self.assertEqual(
            list_line.view_id,
            self.env.ref("base_assembly.assembly_delegation_view_tree_manager"),
        )
        self.assertEqual(
            form_line.view_id,
            self.env.ref("base_assembly.assembly_delegation_view_form_manager"),
        )

    def test_manager_menu_restricted_to_assembly_manager_group(self):
        menu = self.env.ref("base_assembly.assembly_delegation_menu")
        mgr = self.env.ref("base_assembly.assembly_group_manager")
        self.assertIn(mgr, menu.groups_id)

    def test_manager_views_load_without_arch_error(self):
        View = self.env["ir.ui.view"]
        for xmlid in (
            "base_assembly.assembly_delegation_view_tree_manager",
            "base_assembly.assembly_delegation_view_form_manager",
            "base_assembly.assembly_delegation_view_search_manager",
        ):
            vid = self.env.ref(xmlid).id
            vtype = (
                "search"
                if "search" in xmlid
                else ("form" if "form" in xmlid else "list")
            )
            View.get_view(view_id=vid, view_type=vtype)

    def test_default_delegation_list_view_priority_below_manager_screen(self):
        default_tree = self.env.ref("base_assembly.assembly_delegation_view_tree")
        manager_tree = self.env.ref(
            "base_assembly.assembly_delegation_view_tree_manager"
        )
        self.assertLess(default_tree.priority, manager_tree.priority)

    def test_default_delegation_search_priority_below_manager_search(self):
        default_search = self.env.ref("base_assembly.assembly_delegation_view_search")
        manager_search = self.env.ref(
            "base_assembly.assembly_delegation_view_search_manager"
        )
        self.assertLess(default_search.priority, manager_search.priority)
