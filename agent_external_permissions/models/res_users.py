# Copyright 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.api import SUPERUSER_ID

MODULE = "agent_external_permissions"
GROUP_XMLID = "group_agent_user"
GROUP_SALE_OWN = "sales_team.group_sale_salesman"
GROUP_SEE_EMPLOYEES = "group_see_employees_menu"


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
        """Set group_agent_user (and Ventas/Usuario solo documentos propios) if partner is an agent.
        Remove group_see_employees_menu from agents so they don't see the Employees menu.
        """
        group = self.env.ref(f"{MODULE}.{GROUP_XMLID}", raise_if_not_found=False)
        group_sale = self.env.ref(GROUP_SALE_OWN, raise_if_not_found=False)
        group_see_employees = self.env.ref(
            f"{MODULE}.{GROUP_SEE_EMPLOYEES}",
            raise_if_not_found=False,
        )
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
                if group_see_employees and group_see_employees in user.groups_id:
                    cmd.append((3, group_see_employees.id))
                user.sudo().write(vals)
            else:
                cmd = [(3, group.id)]
                if group_see_employees and group_see_employees not in user.groups_id:
                    cmd.append((4, group_see_employees.id))
                user.sudo().write({"groups_id": cmd})

    def _sync_agent_user_group_after_commit(self, user_ids):
        """Run _sync_agent_user_group in a new transaction after commit. Used when creating from portal wizard to avoid 'more than one user type' validation."""
        if not user_ids:
            return
        registry = self.env.registry
        self.env.cr.postcommit.add(
            lambda: self._sync_agent_user_group_postcommit_impl(registry, user_ids)
        )

    def _sync_agent_user_group_postcommit_impl(self, registry, user_ids):
        try:
            with registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                users = env["res.users"].browse(user_ids).exists()
                group = env.ref(f"{MODULE}.{GROUP_XMLID}", raise_if_not_found=False)
                group_sale = env.ref(GROUP_SALE_OWN, raise_if_not_found=False)
                group_see_employees = env.ref(
                    f"{MODULE}.{GROUP_SEE_EMPLOYEES}",
                    raise_if_not_found=False,
                )
                if not group:
                    return
                for user in users:
                    if not user.partner_id or not user.partner_id.agent:
                        continue
                    cmd = [(4, group.id)]
                    vals = {"groups_id": cmd, "share": False}
                    if group_sale and group_sale not in user.groups_id:
                        cmd.append((4, group_sale.id))
                    if group_see_employees and group_see_employees in user.groups_id:
                        cmd.append((3, group_see_employees.id))
                    user.write(vals)
                cr.commit()
        except Exception:
            pass

    def write(self, vals):
        res = super().write(vals)
        if "partner_id" in vals:
            self._sync_agent_user_group()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        if self.env.context.get("no_reset_password"):
            agent_ids = [u.id for u in users if u.partner_id and u.partner_id.agent]
            if agent_ids:
                self._sync_agent_user_group_after_commit(agent_ids)
        else:
            users._sync_agent_user_group()
        return users
