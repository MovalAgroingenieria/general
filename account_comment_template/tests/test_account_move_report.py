# Copyright 2017 Simone Rubino - Agile Business Group
# Copyright 2018 Tecnativa - Pedro M. Baeza
# Copyright 2021-2022 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestAccountInvoiceReport(AccountTestInvoicingCommon):
    """Tests for invoice report integration with base_comment_template."""

    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        # setUpClass is the required name from unittest.TestCase API
        # In Odoo 18, AccountTestInvoicingCommon.setUpClass() takes no params
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
        cls.res_model_id = cls.env.ref("account.model_account_move")

        # Mark account.move as supporting comment templates
        cls.res_model_id.is_comment_template = True

        # Create templates before/after invoice lines
        cls.before_comment = cls._create_comment("before_lines")
        cls.after_comment = cls._create_comment("after_lines")

        # Partner with specific comment templates
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Partner Test",
                "base_comment_template_ids": [
                    (4, cls.before_comment.id),
                    (4, cls.after_comment.id),
                ],
            }
        )

        # Create an invoice to be printed
        cls.invoice = cls.init_invoice(
            "out_invoice",
            partner=cls.partner,
            products=cls.product_a + cls.product_b,
        )

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @classmethod
    def _create_comment(cls, position):
        """Create a comment template for account.move at a given position."""
        return cls.base_comment_model.create(
            {
                "name": "Comment " + position,
                "company_id": cls.company_data["company"].id,
                "position": position,
                "text": "Text " + position,
                # Use the technical model name; model_ids is computed from this.
                "models": "account.move",
            }
        )

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    def test_comments_in_invoice_report(self):
        """Ensure comments are rendered in the invoice QWeb report."""
        # pylint: disable=protected-access
        html, _content_type = self.env["ir.actions.report"]._render_qweb_html(
            "account.report_invoice", self.invoice.ids
        )
        self.assertRegex(str(html), self.before_comment.text)
        self.assertRegex(str(html), self.after_comment.text)

    def test_comments_in_invoice(self):
        """Ensure comment templates are computed on the invoice record."""
        new_invoice = self.init_invoice(
            "out_invoice",
            partner=self.partner,
            products=self.product_a + self.product_b,
        )
        new_invoice.invalidate_recordset(["comment_template_ids"])
        # Reading the field triggers the compute
        comment_ids = new_invoice.comment_template_ids
        self.assertIn(self.after_comment, comment_ids)
        self.assertIn(self.before_comment, comment_ids)
