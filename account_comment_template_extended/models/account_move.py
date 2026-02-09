# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    top_comment = fields.Html(
        help="Comments rendered before the invoice lines.",
    )
    bottom_comment = fields.Html(
        help="Comments rendered after the invoice lines.",
    )

    def action_insert_comments(self):
        """Render and inject comment templates into top and bottom comment fields.

        For each move:
        - Iterate its comment_template_ids.
        - Render each template in the partner language (if any).
        - Concatenate templates with position 'before_lines' into top_comment.
        - Concatenate templates with position 'after_lines' into bottom_comment.
        """
        for move in self:
            top_comment_html = ""
            bottom_comment_html = ""

            # Fallback to partner language, or current user language if absent.
            lang = move.partner_id.lang or self.env.user.lang

            for template in move.comment_template_ids:
                # Ensure rendering is done in the proper language context.
                rendered_comment = move.render_comment(template.with_context(lang=lang))
                if template.position == "before_lines":
                    top_comment_html += rendered_comment
                elif template.position == "after_lines":
                    bottom_comment_html += rendered_comment

            move.top_comment = top_comment_html
            move.bottom_comment = bottom_comment_html
