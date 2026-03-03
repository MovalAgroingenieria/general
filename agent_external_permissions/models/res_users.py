# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models

MODULE = "agent_external_permissions"


class ResUsers(models.Model):
    _inherit = "res.users"

    is_external_agent = fields.Boolean(
        help="Check this if the user is an external agent.",
    )

    is_internal_salesperson = fields.Boolean(
        help="Check this if the user is an internal salesperson.",
    )

    agent_contacts = fields.Many2many(
        comodel_name="res.partner",
        relation="agent_external_permissions_res_partner_external_agent_rel",
        column1="user_id",
        column2="partner_id",
        string="Assigned Contacts",
        help="Contacts assigned to this external agent.",
        readonly=True,
    )

    def _sync_agent_groups(self):
        group_external = self.env.ref(
            f"{MODULE}.group_external_agent", raise_if_not_found=False
        )
        group_internal = self.env.ref(
            f"{MODULE}.group_internal_salesperson", raise_if_not_found=False
        )

        if not group_external or not group_internal:
            return

        for user in self:
            if user.is_external_agent and user.is_internal_salesperson:
                user.is_internal_salesperson = False

            cmds = []
            if user.is_external_agent:
                cmds += [(4, group_external.id), (3, group_internal.id)]
            elif user.is_internal_salesperson:
                cmds += [(4, group_internal.id), (3, group_external.id)]
            else:
                cmds += [(3, group_external.id), (3, group_internal.id)]

            user.sudo().write({"groups_id": cmds})

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        users._sync_agent_groups()  # pylint: disable=protected-access
        return users

    def write(self, vals):
        res = super().write(vals)
        if "is_external_agent" in vals or "is_internal_salesperson" in vals:
            self._sync_agent_groups()
        return res
