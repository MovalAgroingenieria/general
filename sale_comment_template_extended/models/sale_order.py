# Copyright 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    top_comment = fields.Html(default="")
    bottom_comment = fields.Html(default="")

    def action_insert_comments(self):
        """Collect rendered comments from templates into the two HTML fields.
        Idempotent per order; safe to call on multiple records.
        """
        # Known positions (fallback to bottom if unknown)
        before_pos = "before_lines"
        after_pos = "after_lines"

        # Render per order to honor language and order-specific context
        for order in self:
            partner_lang = order.partner_id.lang or None

            # If comment_template_ids is absent/empty, do nothing for this order
            templates = getattr(order, "comment_template_ids", self.env["ir.ui.view"])
            if not templates:
                order.top_comment = ""
                order.bottom_comment = ""
                continue

            # If the relation has a 'sequence' field, use it;
            # otherwise keep natural order
            # pylint: disable=except-pass
            try:
                templates = templates.sorted(key=lambda c: c.sequence)
            except AttributeError:
                # If sequence field doesn't exist, keep natural order
                pass

            top_chunks, bottom_chunks = [], []

            # Prefer a dedicated renderer if available; otherwise fall back to QWeb body
            render_fn = getattr(order, "render_comment", None)

            for comment in templates:
                # Ensure we render with the order's language
                ctx_comment = comment.with_context(lang=partner_lang)

                if callable(render_fn):
                    rendered = render_fn(ctx_comment)
                else:
                    # Generic fallback: try to render a field or a qweb view
                    # if your model uses them
                    rendered = getattr(ctx_comment, "body_html", "") or getattr(
                        ctx_comment, "body", ""
                    )

                rendered = rendered or ""

                if comment._fields.get("position"):
                    pos = comment.position
                else:
                    pos = after_pos  # default

                if pos == before_pos:
                    top_chunks.append(rendered)
                elif pos == after_pos:
                    bottom_chunks.append(rendered)
                else:
                    # Unknown position -> append to bottom by convention
                    bottom_chunks.append(rendered)

            order.top_comment = "".join(top_chunks)
            order.bottom_comment = "".join(bottom_chunks)
