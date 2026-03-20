# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class WizardPreviewPublicationtext(models.TransientModel):
    _name = "wizard.preview.publicationtext"
    _description = "Preview publication or final paragraph text"

    publication_text_preview = fields.Html(
        string="Preview",
        readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get("active_id")
        show_final = self.env.context.get("show_final_paragraph", False)
        if active_id:
            assembly = self.env["assembly.assembly"].browse(active_id)
            if show_final:
                res["publication_text_preview"] = (
                    assembly.get_rendered_final_paragraph()
                )
            else:
                res["publication_text_preview"] = (
                    assembly.get_rendered_publication_text()
                )
        return res
