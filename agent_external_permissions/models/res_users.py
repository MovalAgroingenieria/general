# Copyright 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models

MODULE = "agent_external_permissions"
GROUP_XMLID = "group_agent_user"


class ResUsers(models.Model):
    _inherit = "res.users"

    def _sync_agent_user_group(self):
        """Set group_agent_user if partner is an agent, remove otherwise."""
        group = self.env.ref(f"{MODULE}.{GROUP_XMLID}", raise_if_not_found=False)
        if not group:
            return
        for user in self:
            if not user.partner_id:
                continue
            if user.partner_id.agent:
                user.sudo().write({"groups_id": [(4, group.id)]})
            else:
                user.sudo().write({"groups_id": [(3, group.id)]})

    def write(self, vals):
        res = super().write(vals)
        if "partner_id" in vals:
            self._sync_agent_user_group()
        return res

    @classmethod
    def create(cls, vals_list):
        users = super().create(vals_list)
        users._sync_agent_user_group()
        return users
