# Copyright 2017 Simone Rubino - Agile Business Group
# Copyright 2018 Tecnativa - Pedro M. Baeza
# Copyright 2021-2022 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestSaleOrderReport(TransactionCase):
    """Tests for sale order report integration with base_comment_template."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Disable mail/notifications noise in tests
        cls.env = cls.env(
            context=dict(
                cls.env.context,
                mail_create_nolog=True,
                mail_create_nosubscribe=True,
                mail_notrack=True,
                no_reset_password=True,
                tracking_disable=True,
            )
        )

        cls.base_comment_model = cls.env["base.comment.template"]
        cls.sale_model = cls.env.ref("sale.model_sale_order")

        # Mark sale.order as supporting comment templates
        cls.sale_model.is_comment_template = True

        cls.company = cls.env.company

        # Create comment templates for sale.order (before & after lines)
        cls.sale_before_comment = cls._create_comment_sale_template("before_lines")
        cls.sale_after_comment = cls._create_comment_sale_template("after_lines")

        # Partner with specific comment templates
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Partner Test",
                "company_id": cls.company.id,
                "base_comment_template_ids": [
                    (4, cls.sale_before_comment.id),
                    (4, cls.sale_after_comment.id),
                ],
            }
        )

        # Simple product used on sale order lines
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test Product",
                "type": "service",
                "list_price": 100.0,
                "company_id": cls.company.id,
            }
        )

        # Create a sale order with one line
        cls.sale_order = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "company_id": cls.company.id,
            }
        )
        cls.env["sale.order.line"].create(
            {
                "order_id": cls.sale_order.id,
                "product_id": cls.product.id,
                "product_uom_qty": 1.0,
                "price_unit": cls.product.list_price,
            }
        )

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @classmethod
    def _create_comment_sale_template(cls, position):
        """Create a comment template for sale.order at a given position."""
        return cls.base_comment_model.create(
            {
                "name": "Sale Comment " + position,
                "company_id": cls.company.id,
                "position": position,
                "text": "Sale Text " + position,
                # Use the technical model name; model_ids is computed from this.
                "models": "sale.order",
            }
        )

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    def test_comments_in_sale_order_report(self):
        """Ensure comments are rendered in the sale order QWeb report."""
        html, _content_type = self.env["ir.actions.report"]._render_qweb_html(
            "sale.report_saleorder", self.sale_order.ids
        )
        self.assertRegex(str(html), self.sale_before_comment.text)
        self.assertRegex(str(html), self.sale_after_comment.text)

    def test_comments_in_sale_order_record(self):
        """Ensure comment templates are computed on the sale order record."""
        self.sale_order._compute_comment_template_ids()
        self.assertIn(self.sale_before_comment, self.sale_order.comment_template_ids)
        self.assertIn(self.sale_after_comment, self.sale_order.comment_template_ids)
