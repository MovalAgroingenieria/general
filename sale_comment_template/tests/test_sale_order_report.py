from odoo.tests import Form
from odoo.tests.common import TransactionCase

# pylint: disable=protected-access


class TestAccountInvoiceReport(TransactionCase):
    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.base_comment_model = cls.env["base.comment.template"]

        # -- Sales journal required by v18 for out_invoice
        cls.sale_journal = cls.env["account.journal"].create(
            {
                "name": "Test Sales",
                "code": "TST",
                "type": "sale",
                "company_id": cls.company.id,
            }
        )

        # === Minimal accounting setup (v18: accounts use company_ids,
        # not company_id) ===
        cls.acc_recv = cls.env["account.account"].create(
            {
                "code": "430000TEST",
                "name": "Receivable - Test",
                "reconcile": True,
                "account_type": "asset_receivable",
                "company_ids": [(6, 0, [cls.company.id])],
            }
        )
        cls.acc_income = cls.env["account.account"].create(
            {
                "code": "700000TEST",
                "name": "Income - Test",
                "account_type": "income",
                "company_ids": [(6, 0, [cls.company.id])],
            }
        )
        cls.sale_journal.default_account_id = cls.acc_income  # helpful default

        # -- Comment templates (sale.order / account.move)
        cls.sale_before_comment = cls._create_comment_sale_template(
            "sale.order", "before_lines"
        )
        cls.sale_after_comment = cls._create_comment_sale_template(
            "sale.order", "after_lines"
        )
        cls.move_before_comment = cls._create_comment_sale_template(
            "account.move", "before_lines"
        )
        cls.move_after_comment = cls._create_comment_sale_template(
            "account.move", "after_lines"
        )

        # -- Partner with receivable account
        cls.partner = cls.env["res.partner"].create({"name": "Partner Test"})
        cls.partner.property_account_receivable_id = cls.acc_recv
        cls.partner.base_comment_template_ids = [
            (4, cls.sale_before_comment.id),
            (4, cls.sale_after_comment.id),
            (4, cls.move_before_comment.id),
            (4, cls.move_after_comment.id),
        ]

        # -- Product
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test product",
                "sale_ok": True,
                "type": "service",
                "list_price": 10,
                "invoice_policy": "order",
            }
        )

        # === Assign the income account where this version expects it ===
        tmpl = cls.product.product_tmpl_id
        # v18+ may keep property on template; otherwise older name on category
        if hasattr(tmpl, "property_account_income_id"):
            tmpl.property_account_income_id = cls.acc_income
        elif hasattr(tmpl, "income_account_id"):
            tmpl.income_account_id = cls.acc_income
        else:
            categ = tmpl.categ_id
            if hasattr(categ, "property_account_income_categ_id"):
                categ.property_account_income_categ_id = cls.acc_income

        # -- Sale order
        cls.sale_order = cls._create_sale_order()
        cls.sale_order.action_confirm()

    @classmethod
    def _create_sale_order(cls):
        # Build a simple SO with a single line to invoice
        sale_form = Form(cls.env["sale.order"])
        sale_form.partner_id = cls.partner
        with sale_form.order_line.new() as line_form:
            line_form.product_id = cls.product
        return sale_form.save()

    @classmethod
    def _create_comment_sale_template(cls, models, position):
        # Create a comment template attached to a model and position
        return cls.base_comment_model.create(
            {
                "name": "Comment " + position,
                "position": position,
                "text": "Text " + position,
                "models": models,
            }
        )

    def test_comments_in_sale_order_report(self):
        # The SO report must include before/after comments for sale.order
        res = self.env["ir.actions.report"]._render_qweb_html(
            "sale.report_saleorder", self.sale_order.ids
        )
        self.assertRegex(str(res[0]), self.sale_before_comment.text)
        self.assertRegex(str(res[0]), self.sale_after_comment.text)

    def test_comments_in_generated_invoice(self):
        # Generate customer invoice from SO
        invoice = self.sale_order._create_invoices()[0]

        # account.move comments must be present; sale.order comments must not propagate
        self.assertIn(self.move_before_comment, invoice.comment_template_ids)
        self.assertIn(self.move_after_comment, invoice.comment_template_ids)
        self.assertNotIn(self.sale_before_comment, invoice.comment_template_ids)
        self.assertNotIn(self.sale_after_comment, invoice.comment_template_ids)

        # The invoice report must include the move comments
        res = self.env["ir.actions.report"]._render_qweb_html(
            "account.report_invoice", invoice.ids
        )
        self.assertRegex(str(res[0]), self.move_before_comment.text)
        self.assertRegex(str(res[0]), self.move_after_comment.text)

    def test_comments_in_sale_order(self):
        # The sale order must have both before/after comment templates
        self.assertIn(self.sale_after_comment, self.sale_order.comment_template_ids)
        self.assertIn(self.sale_before_comment, self.sale_order.comment_template_ids)
