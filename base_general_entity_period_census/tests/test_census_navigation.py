# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from lxml import etree

from odoo.tests import TransactionCase, tagged
from odoo.tools.safe_eval import safe_eval


@tagged("post_install", "-at_install")
class TestCensusNavigation(TransactionCase):
    def test_census_menu_children(self):
        parent = self.env.ref(
            "base_general_entity_period_census.menu_general_entity_censuses"
        )
        for menu_id in (
            "menu_general_entity_census", "menu_general_entity_census_lines",
        ):
            menu = self.env.ref("base_general_entity_period_census." + menu_id)
            self.assertEqual(menu.parent_id, parent)

    def test_global_action_disables_creation_only(self):
        action = self.env.ref(
            "base_general_entity_period_census.action_general_entity_census_line"
        )
        context = safe_eval(action.context)
        self.assertFalse(context["create"])
        self.assertFalse(context["import"])
        self.assertTrue(context["edit"])

    def test_census_embedded_lines_still_allow_creation(self):
        view = self.env.ref(
            "base_general_entity_period_census.view_general_entity_census_form"
        )
        result = self.env["general.entity.census"].get_view(view.id, "form")
        arch = etree.fromstring(result["arch"])
        lists = arch.xpath("//field[@name='line_ids']/list")
        self.assertTrue(lists)
        for list_view in lists:
            self.assertNotIn(list_view.get("create"), ("0", "false", "False"))
