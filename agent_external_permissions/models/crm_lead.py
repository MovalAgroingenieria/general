# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = "crm.lead"

    external_agent_ids = fields.Many2many(
        comodel_name="res.users",
        relation="agent_external_permissions_crm_lead_external_agent_rel",
        column1="lead_id",
        column2="user_id",
        string="External Agents",
        help="External agents assigned to this opportunity.",
    )

    @api.onchange("partner_id")
    def _onchange_partner_id_set_external_agents(self):
        """UI helper: prefill agents from the selected contact."""
        for lead in self:
            lead.external_agent_ids = (
                lead.partner_id.external_agent_ids if lead.partner_id else False
            )

    def _check_external_agent_partner_allowed(self, partner):
        """Block assigning partners not linked to the current external agent."""
        self.ensure_one()
        if not partner:
            return
        if not self.env.user.has_group(
            "agent_external_permissions.group_external_agent"
        ):
            return
        if self.env.user not in partner.external_agent_ids:
            raise UserError(
                _(
                    "You can only use contacts where you are assigned as an External Agent."
                )
            )

    @api.model_create_multi
    def create(self, vals_list):
        """
        If partner_id is provided and external_agent_ids is NOT explicitly set,
        initialize external_agent_ids from the partner.

        Context keys:
        - disable_external_agent_sync: disable sync
        """
        if self.env.context.get("disable_external_agent_sync"):
            return super().create(vals_list)

        Partner = self.env["res.partner"]
        new_vals_list = []

        for vals in vals_list:
            vals = dict(vals)  # do not mutate caller dict
            partner = False

            if vals.get("partner_id"):
                partner = Partner.browse(vals["partner_id"]).exists()

                # Guardrail: prevent create with forbidden partner (clean error message)
                # Using a "virtual" record for check: create has no record yet.
                if (
                    self.env.user.has_group(
                        "agent_external_permissions.group_external_agent"
                    )
                    and self.env.user not in partner.external_agent_ids
                ):
                    raise UserError(
                        _(
                            "You can only create opportunities for contacts where you are assigned "
                            "as an External Agent."
                        )
                    )

            if partner and "external_agent_ids" not in vals:
                vals["external_agent_ids"] = [(6, 0, partner.external_agent_ids.ids)]

            new_vals_list.append(vals)

        return super().create(new_vals_list)

    def write(self, vals):
        """
        If partner_id changes and external_agent_ids is NOT explicitly provided,
        sync external_agent_ids from the new partner.

        Context keys:
        - disable_external_agent_sync: disable sync
        """
        if self.env.context.get("disable_external_agent_sync"):
            return super().write(vals)

        if "partner_id" in vals:
            partner = (
                self.env["res.partner"].browse(vals["partner_id"]).exists()
                if vals.get("partner_id")
                else False
            )

            # Guardrail first, so the user doesn't lose access mid-write
            for lead in self:
                lead._check_external_agent_partner_allowed(partner)

            if partner and "external_agent_ids" not in vals:
                vals = dict(vals)
                vals["external_agent_ids"] = [(6, 0, partner.external_agent_ids.ids)]
            elif not partner and "external_agent_ids" not in vals:
                vals = dict(vals)
                vals["external_agent_ids"] = [(5, 0, 0)]

        return super().write(vals)
