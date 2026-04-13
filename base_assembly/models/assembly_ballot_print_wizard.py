# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import base64
import io
import zipfile

from odoo import fields, models
from odoo.exceptions import UserError


class AssemblyBallotPrintWizard(
    models.TransientModel
):  # pylint: disable=no-wizard-in-models
    _name = "assembly.ballot.print.wizard"
    _description = "Print ballots (PDF) for assembly attendees"

    assembly_id = fields.Many2one(
        "assembly.assembly",
        string="Assembly",
        required=True,
        ondelete="cascade",
        check_company=True,
    )
    only_present = fields.Boolean(
        string="Present attendees only",
        default=True,
        help="When enabled, only attendees in Attended (confirmed present) are included. Turn off to include the full list.",
    )
    merge_single_pdf = fields.Boolean(
        string="Merge into one PDF",
        default=True,
        help="Single PDF with one member ballot per page (nominative intro). If disabled, download a ZIP with one PDF per attendee.",
    )
    use_generic_intro_template = fields.Boolean(
        string="Generic intro template (optional)",
        default=False,
        help="Use the assembly-level generic ballot introduction instead of the nominative per-member intro. For special cases only; default member flow uses the attendee-based nominative ballot.",
    )

    def action_print_ballots(self):
        self.ensure_one()
        self.assembly_id._assembly_ensure_not_closed_for_related_changes()
        domain = [("assembly_id", "=", self.assembly_id.id)]
        if self.only_present:
            domain.append(("attendee_state", "=", "confirmed"))
        attendees = self.env["assembly.attendee"].search(domain, order="partner_id, id")
        if not attendees:
            raise UserError(
                self.env._("No attendees match the selected options."),
            )
        report_xmlid = (
            "base_assembly.assembly_attendee_action_report_voting_ballot"
            if self.use_generic_intro_template
            else "base_assembly.assembly_attendee_action_report_voting_ballot_nominative"
        )
        report = self.env.ref(report_xmlid, raise_if_not_found=True)
        if self.merge_single_pdf:
            return report.report_action(attendees.ids)
        ir_report = self.env["ir.actions.report"]
        zbuff = io.BytesIO()
        asm = self.assembly_id
        with zipfile.ZipFile(zbuff, "w", zipfile.ZIP_DEFLATED) as zfile:
            for att in attendees:
                pdf_bytes, _ctype = ir_report._render_qweb_pdf(
                    report.report_name,
                    res_ids=att.ids,
                )
                fname = "Ballot-%s-%s.pdf" % (
                    asm.code or str(asm.id),
                    att.partner_id.id,
                )
                zfile.writestr(fname, pdf_bytes)
        zbuff.seek(0)
        attachment = (
            self.env["ir.attachment"]
            .sudo()
            .create(
                {
                    "name": "Ballots-%s.zip" % (asm.code or str(asm.id)),
                    "type": "binary",
                    "datas": base64.b64encode(zbuff.read()),
                    "mimetype": "application/zip",
                }
            )
        )
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "new",
        }
