# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api

MODULE = "agent_external_permissions"


class ResUsers(models.Model):
    _inherit = "res.users"

    is_external_agent = fields.Boolean(
        string="Is External Agent",
        help="Check this if the user is an external agent.",
    )

    is_internal_salesperson = fields.Boolean(
        string="Is Internal Salesperson",
        help="Check this if the user is an internal salesperson.",
    )

    # Inverse view of partner.external_agent_ids via the same rel table
    agent_contacts = fields.Many2many(
        comodel_name="res.partner",
        relation="res_users_agent_rel",
        column1="user_id",
        column2="partner_id",
        string="Assigned Contacts",
        help="Contacts assigned to this external agent.",
        readonly=True,  # recommended: manage assignment from partner side
    )

    def _sync_agent_groups(self):
        """Ensure group membership matches the boolean flags."""
        group_external = self.env.ref(f"{MODULE}.group_external_agent", raise_if_not_found=False)
        group_internal = self.env.ref(f"{MODULE}.group_internal_salesperson", raise_if_not_found=False)

        if not group_external or not group_internal:
            # If groups are not loaded yet (e.g., during install), do nothing safely.
            return

        for user in self:
            # If both are ticked, external wins? Better: external has priority OR enforce exclusivity.
            # Here we enforce exclusivity: if one is True, we unset the other.
            if user.is_external_agent and user.is_internal_salesperson:
                user.is_internal_salesperson = False

            # Build m2m commands for groups_id
            cmds = []
            if user.is_external_agent:
                cmds += [(4, group_external.id), (3, group_internal.id)]
            elif user.is_internal_salesperson:
                cmds += [(4, group_internal.id), (3, group_external.id)]
            else:
                # none selected -> remove both
                cmds += [(3, group_external.id), (3, group_internal.id)]

            # Use sudo to avoid permission issues when normal users are edited by admins
            user.sudo().write({"groups_id": cmds})

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        # Only sync if flags are present in create vals or defaults might apply
        users._sync_agent_groups()
        return users

    def write(self, vals):
        res = super().write(vals)
        if "is_external_agent" in vals or "is_internal_salesperson" in vals:
            self._sync_agent_groups()
        return res
