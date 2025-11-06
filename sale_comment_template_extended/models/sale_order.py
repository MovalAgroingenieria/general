# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    top_comment = fields.Html(string="Top Comment", default="")
    bottom_comment = fields.Html(string="Bottom Comment", default="")

    def action_insert_comments(self):
        """Collect rendered comments from templates into the two HTML fields.
        Safe to call on multiple records.
        """
        for order in self:
            lang = order.partner_id.lang or None
            top_comment_text = []
            bottom_comment_text = []

            # If comment_template_ids is empty or missing, nothing happens.
            for comment in getattr(order, "comment_template_ids", []):
                rendered = order.render_comment(comment.with_context(lang=lang))
                if comment.position == "before_lines":
                    top_comment_text.append(rendered or "")
                elif comment.position == "after_lines":
                    bottom_comment_text.append(rendered or "")

            order.top_comment = "".join(top_comment_text)
            order.bottom_comment = "".join(bottom_comment_text)
