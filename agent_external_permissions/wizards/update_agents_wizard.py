# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class UpdateAgentsWizard(models.TransientModel):
    _name = "update.agents.wizard"
    _description = "Update external agents on opportunities"

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Contact",
        required=True,
    )
    update_existing = fields.Boolean(
        string="Update existing opportunities",
        default=True,
        help="If enabled, update external agents on all existing opportunities for this contact.",
    )
    create_new_opportunities = fields.Boolean(
        string="Create a new opportunity if none exist",
        default=False,
        help="If enabled and the contact has no opportunities, create one opportunity.",
    )
    opportunity_count = fields.Integer(
        string="Existing opportunities",
        compute="_compute_opportunity_count",
        readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ctx = self.env.context
        if (
                "partner_id" in fields_list
                and ctx.get("active_model") == "res.partner"
                and ctx.get("active_id")
        ):
            res["partner_id"] = ctx["active_id"]
        return res

    @api.depends("partner_id")
    def _compute_opportunity_count(self):
        Lead = self.env["crm.lead"]
        for wizard in self:
            if wizard.partner_id:
                wizard.opportunity_count = Lead.search_count(
                    [
                        ("partner_id", "=", wizard.partner_id.id),
                        ("type", "=", "opportunity"),
                    ]
                )
            else:
                wizard.opportunity_count = 0

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id:
            self.update_existing = True

    def action_update_agents(self):
        self.ensure_one()

        if not self.partner_id.external_agent_ids:
            raise UserError(
                _(
                    "This contact has no external agents assigned. "
                    "Please assign agents to the contact first."
                )
            )

        Lead = self.env["crm.lead"]
        opportunities = Lead.search(
            [
                ("partner_id", "=", self.partner_id.id),
                ("type", "=", "opportunity"),
            ]
        )

        agent_m2m_cmd = [(6, 0, self.partner_id.external_agent_ids.ids)]
        updated_count = 0
        created_count = 0

        if opportunities and self.update_existing:
            opportunities.with_context(skip_external_agent_propagation=True).write(
                {"external_agent_ids": agent_m2m_cmd}
            )
            updated_count = len(opportunities)

        if self.create_new_opportunities and not opportunities:
            Lead.with_context(skip_external_agent_propagation=True).create(
                {
                    "name": _("Opportunity for %s") % self.partner_id.name,
                    "partner_id": self.partner_id.id,
                    "type": "opportunity",
                    "external_agent_ids": agent_m2m_cmd,
                }
            )
            created_count = 1

        if not (updated_count or created_count):
            return self._notification(
                title=_("Information"),
                message=_("No opportunities were updated or created."),
                notif_type="info",
            )

        parts = []
        if updated_count:
            parts.append(_("Updated %s opportunities") % updated_count)
        if created_count:
            parts.append(_("Created %s opportunity") % created_count)

        return self._notification(
            title=_("Success"),
            message=" | ".join(parts),
            notif_type="success",
        )

    def _notification(self, title, message, notif_type):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": notif_type,
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
