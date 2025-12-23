# Copyright 2025 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    top_comment = fields.Html(
        help="Rendered comment content displayed above the move lines.",
    )
    bottom_comment = fields.Html(
        help="Rendered comment content displayed below the move lines.",
    )

    def action_insert_comments(self):
        """Render and place comment templates into top/bottom HTML fields.

        The rendering language is taken from the partner (preferred) and falls
        back to the current environment language.

        This method is compatible with Odoo 18 and follows OCA guidelines:
        - Works record-by-record (no reliance on singleton).
        - Avoids inefficient string concatenation in loops.
        - Uses a single write/update per record.
        """
        for picking in self:
            lang = picking.partner_id.lang or picking.env.lang

            top_chunks = []
            bottom_chunks = []

            # If there are no templates, just clear existing content
            # (change this behavior if you prefer keeping previous values).
            templates = picking.comment_template_ids
            if not templates:
                picking.update({"top_comment": False, "bottom_comment": False})
                continue

            for template in templates:
                # Ensure language context during rendering.
                rendered = (
                    picking.with_context(lang=lang).render_comment(template) or ""
                )

                # Place rendered HTML depending on template position.
                if template.position == "before_lines":
                    top_chunks.append(rendered)
                elif template.position == "after_lines":
                    bottom_chunks.append(rendered)

            picking.update(
                {
                    "top_comment": "".join(top_chunks) or False,
                    "bottom_comment": "".join(bottom_chunks) or False,
                }
            )

        return True
