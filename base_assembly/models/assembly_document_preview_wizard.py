# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AssemblyDocumentPreviewWizard(
    models.TransientModel
):  # pylint: disable=no-wizard-in-models
    _name = "assembly.document.preview.wizard"
    _description = "Preview rendered assembly document HTML"

    assembly_id = fields.Many2one(
        "assembly.assembly",
        string="Assembly",
        required=True,
        readonly=True,
        ondelete="cascade",
    )
    document_type = fields.Selection(
        [
            ("publication", "Publication / convocation"),
            ("delegation_body", "Delegation document body"),
            ("delegation_footer", "Delegation footer"),
            ("delegation_combined", "Delegation (intro + footer)"),
            ("ballot_intro", "Ballot introduction"),
            ("ballot_nominative", "Nominative ballot introduction"),
        ],
        string="Document",
        required=True,
        default="publication",
    )
    preview_html = fields.Html(string="Rendered preview", readonly=True, sanitize=False)

    def _preview_html_from_selection(self):
        """HTML string for current ``assembly_id`` and ``document_type``.

        Returns ``""`` only when ``assembly_id`` or ``document_type`` is missing;
        otherwise delegates to assembly render helpers (non-empty for valid types).
        """
        self.ensure_one()
        asm, doc = self.assembly_id, self.document_type
        if not asm or not doc:
            return ""
        if doc == "publication":
            html = asm.get_rendered_publication_text()
        elif doc == "delegation_body":
            html = asm.get_rendered_delegation_document_text()
        elif doc == "delegation_footer":
            html = asm.get_rendered_delegation_footer_text()
        elif doc == "delegation_combined":
            html = asm.get_rendered_delegation()
        elif doc == "ballot_intro":
            html = asm.get_rendered_ballot_intro_text()
        else:
            html = asm.get_rendered_ballot_nominative_intro_text()
        return str(html) if html else ""

    def action_refresh_preview(self):
        self.ensure_one()
        self.write({"preview_html": self._preview_html_from_selection()})
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Preview rendered document"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    @api.onchange("document_type", "assembly_id")
    def _onchange_document_type_refresh(self):
        if self.assembly_id and self.document_type:
            self.preview_html = self._preview_html_from_selection()
