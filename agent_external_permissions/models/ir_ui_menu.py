# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models

MODULE = "agent_external_permissions"

# Root menu xmlids to hide from external agents (modules may be uninstalled).
EXTERNAL_AGENT_MENU_BLACKLIST = [
    "board.menu_board_my_dash",
    "hr.menu_hr_root",
    "hr_expense.menu_hr_expense_root",
    "spreadsheet_dashboard.spreadsheet_dashboard_menu_root",
]


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    @api.model
    def _visible_menu_ids(self, debug=False):
        visible = super()._visible_menu_ids(debug=debug)
        if not self.env.user.has_group(f"{MODULE}.group_external_agent"):
            return visible
        ir_model_data = self.env["ir.model.data"]
        blacklist_ids = set()
        for xmlid in EXTERNAL_AGENT_MENU_BLACKLIST:
            menu_id = (
                ir_model_data._xmlid_to_res_id(  # pylint: disable=protected-access
                    xmlid, raise_if_not_found=False
                )
            )
            if menu_id:
                blacklist_ids.add(menu_id)
        if not blacklist_ids:
            return visible
        descendants = self.with_context(**{"ir.ui.menu.full_list": True}).search(
            [("id", "child_of", list(blacklist_ids))]
        )
        return visible - set(descendants.ids)
