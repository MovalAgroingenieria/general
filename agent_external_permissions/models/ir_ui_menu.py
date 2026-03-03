# Copyright 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models

MODULE = "agent_external_permissions"
GROUP_XMLID = "group_agent_user"
HR_MENU_XMLID = "hr.menu_hr_root"


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    @api.model
    def _visible_menu_ids(self, debug=False):
        """Hide Employees (HR) menu from agent users."""
        visible = super()._visible_menu_ids(debug=debug)
        if not self.env.user.has_group(f"{MODULE}.{GROUP_XMLID}"):
            return visible
        menu_id = self.env["ir.model.data"]._xmlid_to_res_id(
            HR_MENU_XMLID,
            raise_if_not_found=False,
        )
        if not menu_id:
            return visible
        with_context = self.with_context(**{"ir.ui.menu.full_list": True})
        hr_menus = with_context.search([("id", "child_of", [menu_id])])
        return visible - set(hr_menus.ids)
