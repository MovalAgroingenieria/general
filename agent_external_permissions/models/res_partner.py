# Copyright 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models

MODULE = "agent_external_permissions"
GROUP_XMLID = "group_agent_user"


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _sync_agent_user_group(self):
        """Add or remove group_agent_user for users linked to this partner."""
        group = self.env.ref(f"{MODULE}.{GROUP_XMLID}", raise_if_not_found=False)
        if not group:
            return
        for partner in self:
            if not partner.user_ids:
                continue
            if partner.agent:
                partner.user_ids.sudo().write({
                    "groups_id": [(4, group.id)],
                })
            else:
                partner.user_ids.sudo().write({
                    "groups_id": [(3, group.id)],
                })

    def write(self, vals):
        res = super().write(vals)
        if "agent" in vals:
            self._sync_agent_user_group()
        return res
