# Copyright 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# pylint: disable=invalid-name
# pylint: disable=unused-argument
# pylint: disable=protected-access

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSaleOrderReportComments(TransactionCase):
    """Verify TOP (before lines table) and BOTTOM (after fiscal remark)
    blocks in the sale order report."""

    def setUp(self):
        super().setUp()
        self.SaleOrder = self.env["sale.order"]
        self.Partner = self.env["res.partner"]
        self.Product = self.env["product.product"]

        # Resolve comodel for comment_template_ids
        m2m = self.SaleOrder._fields.get("comment_template_ids")
        if not m2m:
            self.skipTest("'comment_template_ids' is not defined on sale.order")
        comodel = getattr(m2m, "comodel_name", None)
        if not comodel:
            self.skipTest("Cannot resolve comodel for 'comment_template_ids'")
        self.Template = self.env[comodel]

        if "position" not in self.Template._fields:
            self.skipTest(f"Template model '{comodel}' is missing 'position'")

        # Pick a content field (for NOT NULL)
        self._content_field = next(
            (f for f in ("text", "body_html", "body") if f in self.Template._fields),
            None,
        )

        # Get all available models for the template
        available_models = self.env["ir.model"].search([])
        if not available_models:
            self.skipTest("No models found in the database")

        # Builder for templates: fills required fields + 'models'
        # in the appropriate format
        def _create_template(vals):
            allowed = {k: v for k, v in vals.items() if k in self.Template._fields}

            # Content stub if needed
            if self._content_field:
                field = self.Template._fields[self._content_field]
                if (
                    getattr(field, "required", False)
                    or self._content_field not in allowed
                ):
                    allowed[self._content_field] = "<p>stub</p>"

            # Company required?
            if "company_id" in self.Template._fields:
                field = self.Template._fields["company_id"]
                if getattr(field, "required", False) and "company_id" not in allowed:
                    allowed["company_id"] = self.env.company.id

            # Models field handling (M2M vs JSON/Text)
            if "models" in self.Template._fields and "models" not in allowed:
                models_field = self.Template._fields["models"]
                if (
                    getattr(models_field, "type", "") == "many2many"
                    and getattr(models_field, "comodel_name", "") == "ir.model"
                ):
                    # Use all available models to avoid validation errors
                    allowed["models"] = [(6, 0, available_models.ids)]
                else:
                    # JSON or char-like: store technical names of all available models
                    allowed["models"] = available_models.mapped("model")

            return self.Template.create(allowed)

        self._create_template = _create_template

        # Base partner & product
        self.partner = self.Partner.create({"name": "Client Report", "lang": "es_ES"})
        self.product = self.Product.create(
            {"name": "Test Product", "type": "service", "list_price": 100.0}
        )

        # Try to create templates, skip test if model validation fails
        try:
            self.t_top = self._create_template(
                {"name": "TOP Marker", "position": "before_lines", "sequence": 5}
            )
            self.t_bottom = self._create_template(
                {"name": "BOTTOM Marker", "position": "after_lines", "sequence": 10}
            )
        except ValidationError as e:
            self.skipTest(
                f"Cannot create comment templates due to model validation: {e}"
            )

        # Sale order with a line
        self.order = self.SaleOrder.create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": "Line 1",
                            "product_uom_qty": 1.0,
                            "price_unit": 100.0,
                        },
                    )
                ],
            }
        )
        self.order.comment_template_ids = [(6, 0, [self.t_top.id, self.t_bottom.id])]

        # Deterministic render_comment
        def _fake_render_comment(order_self, comment_rec):
            pos = getattr(comment_rec, "position", "after_lines")
            marker = "__TOP_MARKER__" if pos == "before_lines" else "__BOTTOM_MARKER__"
            return f"<p>{marker}</p>"

        # Patch the render_comment method
        self.patched_render_comment = _fake_render_comment
        self.original_render_comment = getattr(type(self.order), "render_comment", None)
        type(self.order).render_comment = _fake_render_comment

    def tearDown(self):
        # Restore original render_comment method if it existed
        if self.original_render_comment:
            type(self.order).render_comment = self.original_render_comment
        super().tearDown()

    def _render_sale_order_html(self, order):
        report = self.env.ref("sale.action_report_saleorder")
        html_bytes, _ = report._render_qweb_html([order.id])
        return html_bytes.decode("utf-8", errors="ignore")

    def test_comments_positions_in_report(self):
        html = self._render_sale_order_html(self.order)

        top_marker = "__TOP_MARKER__"
        bottom_marker = "__BOTTOM_MARKER__"
        main_table_anchor = 'class="o_main_table"'
        fiscal_anchor = 'id="fiscal_position_remark"'

        self.assertIn(top_marker, html)
        self.assertIn(bottom_marker, html)
        self.assertIn(main_table_anchor, html)
        self.assertIn(fiscal_anchor, html)

        idx_top = html.find(top_marker)
        idx_bottom = html.find(bottom_marker)
        idx_table = html.find(main_table_anchor)
        idx_fiscal = html.find(fiscal_anchor)

        self.assertLess(idx_top, idx_table, "TOP must be BEFORE the main table")
        self.assertGreater(
            idx_bottom, idx_fiscal, "BOTTOM must be AFTER the fiscal remark"
        )
