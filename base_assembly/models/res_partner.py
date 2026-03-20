# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

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
    assembly_representation_ids = fields.One2many(
        "assembly.representation",
        "partner_id",
        string="Representations (as principal)",
    )
    count_assembly_attendees = fields.Integer(
        string="Attendances count",
        compute="_compute_assembly_counts",
    )
    count_assembly_delegations = fields.Integer(
        string="Delegations count",
        compute="_compute_assembly_counts",
    )
    count_assembly_representations = fields.Integer(
        string="Representations count",
        compute="_compute_assembly_counts",
    )
    assembly_excluded = fields.Boolean(
        string="Excluded from assemblies",
        default=False,
        help="If set, this partner is excluded from generated attendee lists.",
    )

    @api.depends(
        "assembly_attendee_ids",
        "assembly_delegation_ids",
        "assembly_representation_ids",
    )
    def _compute_assembly_counts(self):
        for rec in self:
            rec.count_assembly_attendees = len(rec.assembly_attendee_ids)
            rec.count_assembly_delegations = len(rec.assembly_delegation_ids)
            rec.count_assembly_representations = len(rec.assembly_representation_ids)

    def action_open_assembly_attendees(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Assembly attendances"),
            "res_model": "assembly.attendee",
            "view_mode": "list,form",
            "domain": [("partner_id", "=", self.id)],
            "context": {"default_partner_id": self.id},
        }

    def action_open_assembly_delegations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Delegations (as delegator)"),
            "res_model": "assembly.delegation",
            "view_mode": "list,form",
            "domain": [("partner_id", "=", self.id)],
            "context": {"default_partner_id": self.id},
        }

    def action_open_assembly_representations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Representations (as principal)"),
            "res_model": "assembly.representation",
            "view_mode": "list,form",
            "domain": [("partner_id", "=", self.id)],
            "context": {"default_partner_id": self.id},
        }
