# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner", "assembly.mixin.window_action"]

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
        for partner in self:
            partner.count_assembly_attendees = len(partner.assembly_attendee_ids)
            partner.count_assembly_delegations = len(partner.assembly_delegation_ids)

    def action_open_assembly_attendees(self):
        return self._action_window(
            "assembly.attendee",
            self.env._("Assembly attendances"),
            "list,form",
            domain=[("partner_id", "=", self.id)],
            context={"default_partner_id": self.id},
        )

    def action_open_assembly_delegations(self):
        return self._action_window(
            "assembly.delegation",
            self.env._("Delegations (as delegator)"),
            "list,form",
            domain=[("partner_id", "=", self.id)],
            context={"default_partner_id": self.id},
        )
