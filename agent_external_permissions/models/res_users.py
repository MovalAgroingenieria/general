# Copyright 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models

MODULE = "agent_external_permissions"
GROUP_XMLID = "group_agent_user"
GROUP_SALE_OWN = "sales_team.group_sale_salesman"  # Ventas / Usuario: Solo mostrar documentos propios


class ResUsers(models.Model):
    _inherit = "res.users"

    is_external_agent = fields.Boolean(
        string="External agent",
        compute="_compute_is_external_agent",
        store=True,
        readonly=True,
    )
    is_internal_salesperson = fields.Boolean(
        string="Internal salesperson",
        compute="_compute_is_internal_salesperson",
        store=True,
        readonly=True,
    )
    agent_contacts = fields.Many2many(
        comodel_name="res.partner",
        string="Assigned contacts",
        compute="_compute_agent_contacts",
        readonly=True,
    )

    @api.depends("partner_id", "partner_id.agent")
    def _compute_is_external_agent(self):
        for user in self:
            user.is_external_agent = bool(user.partner_id and user.partner_id.agent)

    @api.depends()
    def _compute_is_internal_salesperson(self):
        for user in self:
            user.is_internal_salesperson = False

    @api.depends("partner_id")
    def _compute_agent_contacts(self):
        for user in self:
            if user.partner_id:
                user.agent_contacts = self.env["res.partner"].search(
                    [("agent_ids", "in", [user.partner_id.id])]
                )
            else:
                user.agent_contacts = self.env["res.partner"].browse()

    def _sync_agent_user_group(self):
        """Set group_agent_user (and Ventas/Usuario solo documentos propios) if partner is an agent."""
        group = self.env.ref(f"{MODULE}.{GROUP_XMLID}", raise_if_not_found=False)
        group_sale = self.env.ref(GROUP_SALE_OWN, raise_if_not_found=False)
        if not group:
            return
        for user in self:
            if not user.partner_id:
                continue
            if user.partner_id.agent:
                cmd = [(4, group.id)]
                vals = {"groups_id": cmd}
                if group_sale and group_sale not in user.groups_id:
                    cmd.append((4, group_sale.id))
                    vals["share"] = False
                user.sudo().write(vals)
            else:
                user.sudo().write({"groups_id": [(3, group.id)]})

    def write(self, vals):
        res = super().write(vals)
        if "partner_id" in vals:
            self._sync_agent_user_group()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        users._sync_agent_user_group()
        return users
