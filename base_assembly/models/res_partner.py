# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.osv import expression


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner"]

    assembly_attendee_ids = fields.One2many(
        "assembly.attendee",
        "partner_id",
        string="Assembly attendances",
    )
    assembly_delegation_ids = fields.One2many(
        "assembly.delegation",
        "partner_id",
        string="Delegations (as delegator)",
    )
    assembly_representation_owner_ids = fields.One2many(
        "assembly.representation",
        "owner_partner_id",
        string="Representations (as represented member)",
    )
    assembly_representation_agent_ids = fields.One2many(
        "assembly.representation",
        "agent_partner_id",
        string="Representations (as agent)",
    )
    count_assembly_attendees = fields.Integer(
        string="Attendances count",
        compute="_compute_assembly_counts",
    )
    count_assembly_delegations = fields.Integer(
        string="Delegations count",
        compute="_compute_assembly_counts",
    )
    assembly_excluded = fields.Boolean(
        string="Excluded from assemblies",
        default=False,
        help="If set, this partner is excluded from generated attendee lists.",
    )

    @api.depends("assembly_attendee_ids", "assembly_delegation_ids")
    def _compute_assembly_counts(self):
        for record in self:
            record.count_assembly_attendees = len(record.assembly_attendee_ids)
            record.count_assembly_delegations = len(record.assembly_delegation_ids)

    def action_open_assembly_attendees(self):
        domain = expression.AND(
            [
                [("partner_id", "=", self.id)],
                [("assembly_id.active", "=", True)],
            ]
        )
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Assembly attendances"),
            "res_model": "assembly.attendee",
            "view_mode": "list,form",
            "target": "current",
            "domain": domain,
            "context": {"default_partner_id": self.id},
        }

    def action_open_assembly_delegations(self):
        domain = expression.AND(
            [
                [("partner_id", "=", self.id)],
                [("assembly_id.active", "=", True)],
            ]
        )
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Delegations (as delegator)"),
            "res_model": "assembly.delegation",
            "view_mode": "list,form",
            "target": "current",
            "domain": domain,
            "context": {"default_partner_id": self.id},
        }
