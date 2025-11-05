# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from ast import literal_eval

from lxml import etree
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPaymentOrderViews(TransactionCase):
    """
    Validate that the inherited views are properly applied in Odoo 18:

    1) account.payment.order form inherits and injects a context with
       'list_view_ref' into the one2many field 'payment_ids'.

    2) account.payment list view inherits and adds the 'payment_line_date' field
       after the 'name' column.
    """

    def _get_view_arch(self, model, view_id, view_type):
        """Return the combined (final) arch for a given model/view."""
        res = self.env[model].fields_view_get(view_id=view_id, view_type=view_type)
        return etree.fromstring(
            res["arch"].encode()
        )  # pylint: disable=c-extension-no-member

    def test_form_inherit_sets_list_view_ref_on_payment_ids(self):
        # Base parent form view of payment order (from account_payment_order)
        parent_xmlid = "account_payment_order.account_payment_order_form"
        parent_view = self.env.ref(parent_xmlid)

        # Get the combined (inherited) arch of that form
        root = self._get_view_arch(
            "account.payment.order", parent_view.id, view_type="form"
        )

        # Find the payment_ids field in the final arch
        field = root.xpath(".//field[@name='payment_ids']")
        self.assertTrue(field, "payment_ids must exist in the combined form view")
        field = field[0]

        # Extract and evaluate the context dict from the attribute
        ctx_text = (field.get("context") or "").strip()
        self.assertTrue(ctx_text, "payment_ids must carry a context attribute")

        # Odoo stores context as a python-literal string (single quotes allowed)
        ctx = literal_eval(ctx_text)
        self.assertIn(
            "list_view_ref",
            ctx,
            "payment_ids.context must define 'list_view_ref'",
        )
        expected_ref = (
            "account_payment_order_payment_line_date."
            "view_account_payment_tree_payment_order"
        )
        self.assertEqual(
            ctx["list_view_ref"],
            expected_ref,
            "list_view_ref must point to the custom list view for payment lines",
        )

    def test_list_inherit_adds_payment_line_date_after_name(self):
        # Target list view (tree) inherited by our module
        base_list_xmlid = (
            "account_payment_order.view_account_payment_tree_payment_order"
        )
        base_list_view = self.env.ref(base_list_xmlid)

        # Get the combined (inherited) arch of that list
        root = self._get_view_arch(
            "account.payment", base_list_view.id, view_type="list"
        )

        # Collect column names in order
        cols = root.xpath("./field")
        names = [c.get("name") for c in cols if c.get("name")]

        # Ensure both fields are present
        self.assertIn("name", names, "'name' must exist in the list columns")
        self.assertIn(
            "payment_line_date",
            names,
            "'payment_line_date' must be present in the list columns",
        )

        # Ensure payment_line_date is placed AFTER name, as per xpath rule
        self.assertLess(
            names.index("name"),
            names.index("payment_line_date"),
            "'payment_line_date' must appear after 'name' in the list",
        )
