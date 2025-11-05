# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields


class StockPicking(models.Model):
    _inherit = "stock.picking"

    top_comment = fields.Html(
        string='Top Comment',
    )
    bottom_comment = fields.Html(
        string='Bottom Comment',
    )

    def action_insert_comments(self):
        for record in self:
            top_comment_text = bottom_comment_text = ""
            for comment in record.comment_template_ids:
                lang = record.partner_id.lang if record.partner_id else None
                rendered_comment = record.render_comment(
                    comment.with_context(lang=lang))
                if comment.position == 'before_lines':
                    top_comment_text += rendered_comment
                elif comment.position == 'after_lines':
                    bottom_comment_text += rendered_comment
            record.top_comment = top_comment_text
            record.bottom_comment = bottom_comment_text
