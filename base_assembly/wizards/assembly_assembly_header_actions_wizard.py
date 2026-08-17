# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AssemblyAssemblyHeaderActionsWizard(models.TransientModel):
    _name = "assembly.assembly.header.actions.wizard"
    _description = "Assembly header secondary actions"

    assembly_id = fields.Many2one(
        "assembly.assembly",
        required=True,
        readonly=True,
        check_company=True,
    )
    assembly_state = fields.Selection(
        related="assembly_id.assembly_state",
        readonly=True,
    )
    has_attendees = fields.Boolean(compute="_compute_has_attendees")

    @api.depends("assembly_id", "assembly_id.attendee_ids")
    def _compute_has_attendees(self):
        for record in self:
            record.has_attendees = bool(record.assembly_id.attendee_ids)

    def action_wizard_recompute_votes(self):
        self.ensure_one()
        self.assembly_id.action_recompute_attendee_votes()
        return {"type": "ir.actions.act_window_close"}

    def action_wizard_document_preview(self):
        self.ensure_one()
        return self.assembly_id.action_open_document_preview_wizard()

    def action_wizard_ballot_print(self):
        self.ensure_one()
        return self.assembly_id.action_open_ballot_print_wizard()

    def action_wizard_mail_publication(self):
        self.ensure_one()
        return self.assembly_id.action_mail_compose_publication()

    def action_wizard_mail_ballot_intro(self):
        self.ensure_one()
        return self.assembly_id.action_mail_compose_ballot_intro()

    def action_wizard_mail_delegation(self):
        self.ensure_one()
        return self.assembly_id.action_mail_compose_delegation()

    def action_wizard_cancel_assembly(self):
        self.ensure_one()
        self.assembly_id.action_cancel()
        return {"type": "ir.actions.act_window_close"}

    def action_wizard_close_assembly(self):
        self.ensure_one()
        self.assembly_id.action_close()
        return {"type": "ir.actions.act_window_close"}
