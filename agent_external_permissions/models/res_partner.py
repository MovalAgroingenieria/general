# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from collections import defaultdict

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    external_agent_ids = fields.Many2many(
        comodel_name="res.users",
        relation="agent_external_permissions_res_partner_external_agent_rel",
        column1="partner_id",
        column2="user_id",
        string="External Agents",
        help="External agents assigned to this contact.",
    )

    def _propagate_external_agents_to_opportunities(self):
        """
        Propagate external_agent_ids to related opportunities.

        Target:
        - crm.lead records where type='opportunity' and partner_id in self

        Context keys:
        - skip_external_agent_propagation: disable propagation
        - force_external_agent_propagation_sudo: propagate using sudo (use sparingly)
        """
        if self.env.context.get("skip_external_agent_propagation"):
            return

        Lead = self.env["crm.lead"]
        if self.env.context.get("force_external_agent_propagation_sudo"):
            Lead = Lead.sudo()

        leads = Lead.search(
            [
                ("type", "=", "opportunity"),
                ("partner_id", "in", self.ids),
            ]
        )
        if not leads:
            return

        # Group lead ids by partner_id in one pass (fast and predictable)
        lead_ids_by_partner = defaultdict(list)
        for lead in leads:
            lead_ids_by_partner[lead.partner_id.id].append(lead.id)

        for partner in self:
            partner_lead_ids = lead_ids_by_partner.get(partner.id)
            if not partner_lead_ids:
                continue

            Lead.browse(partner_lead_ids).write(
                {"external_agent_ids": [(6, 0, partner.external_agent_ids.ids)]}
            )

    def write(self, vals):
        """
        If external_agent_ids changed, propagate to related opportunities.

        Notes:
        - Safe for multi-record writes.
        - Propagation happens AFTER the partner write (so partner has the final values).
        """
        must_propagate = "external_agent_ids" in vals and not self.env.context.get(
            "skip_external_agent_propagation"
        )

        res = super().write(vals)

        if must_propagate:
            self._propagate_external_agents_to_opportunities()

        return res
