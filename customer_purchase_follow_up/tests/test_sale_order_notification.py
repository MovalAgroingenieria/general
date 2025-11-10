# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# We use unittest's canonical setUpClass name; silence pylint for this file.
# pylint: disable=invalid-name

from datetime import date
from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestSaleOrderNotification(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.Product = cls.env["product.product"]
        cls.SaleOrder = cls.env["sale.order"]

        # Base partner with flags enabled and currently "notified"
        cls.partner = cls.Partner.create(
            {
                "name": "Notified Customer",
                "client_notified": True,
                "purchase_notifications_enabled": True,
                "last_notification_date": date.today(),
            }
        )

        # Partner that must NOT be reset because the option is disabled
        cls.partner_opt_out = cls.Partner.create(
            {
                "name": "Opt-out Customer",
                "client_notified": True,
                "purchase_notifications_enabled": False,
                "last_notification_date": date.today(),
            }
        )

        # Partner that must NOT be reset because it's not currently notified
        cls.partner_not_notified = cls.Partner.create(
            {
                "name": "Not-notified Customer",
                "client_notified": False,
                "purchase_notifications_enabled": True,
                "last_notification_date": False,
            }
        )

        # Minimal product to confirm a sale order
        cls.product = cls.Product.create(
            {
                "name": "Test Service",
                "type": "service",
                "list_price": 100.0,
            }
        )

    # Helpers
    def _make_order(self, partner):
        order = self.SaleOrder.create({"partner_id": partner.id})
        self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "product_uom_qty": 1.0,
                "price_unit": 100.0,
                "name": "Test line",
            }
        )
        return order

    def test_action_confirm_resets_partner_notification(self):
        """Upon confirmation, flags are reset when partner meets conditions."""
        order = self._make_order(self.partner)

        # Preconditions
        self.assertTrue(order.partner_id.client_notified)
        self.assertTrue(order.partner_id.purchase_notifications_enabled)
        self.assertTrue(order.partner_id.last_notification_date)

        # action_confirm uses a context flag to avoid duplicate reset in write()
        order.action_confirm()

        order.partner_id.invalidate_recordset()
        self.assertFalse(order.partner_id.client_notified)
        self.assertFalse(order.partner_id.last_notification_date)

    def test_write_state_sale_triggers_reset(self):
        """An explicit write to 'sale' triggers the reset (no skip context)."""
        order = self._make_order(self.partner)

        # Ensure initial draft state
        self.assertEqual(order.state, "draft")

        # Writing state='sale' should trigger the reset here
        order.write({"state": "sale"})

        order.partner_id.invalidate_recordset()
        self.assertFalse(order.partner_id.client_notified)
        self.assertFalse(order.partner_id.last_notification_date)

    def test_skip_context_avoids_duplicate_reset(self):
        """When coming from action_confirm, write() must not duplicate the reset."""
        order = self._make_order(self.partner)

        order.action_confirm()
        self.assertFalse(order.partner_id.client_notified)
        self.assertFalse(order.partner_id.last_notification_date)

        # Simulate later flags being re-set by other logic
        order.partner_id.write(
            {
                "client_notified": True,
                "last_notification_date": date.today(),
            }
        )
        # Write with the same skip flag used by action_confirm
        order.with_context(skip_reset_partner_notification=True).write(
            {"state": "sale"}
        )

        # With skip flag present, no reset should happen now
        order.partner_id.invalidate_recordset()
        self.assertTrue(order.partner_id.client_notified)
        self.assertTrue(order.partner_id.last_notification_date)

    def test_filters_only_reset_when_flags_allow(self):
        """_reset_partner_notification filters orders based on partner flags."""
        order_ok = self._make_order(self.partner)
        order_opt_out = self._make_order(self.partner_opt_out)
        order_not_notified = self._make_order(self.partner_not_notified)

        # Call the private helper with all three orders; only
        # order_ok should be affected
        # pylint: disable=protected-access
        order_ok._reset_partner_notification(
            order_ok | order_opt_out | order_not_notified
        )

        # order_ok partner is reset
        order_ok.partner_id.invalidate_recordset()
        self.assertFalse(order_ok.partner_id.client_notified)
        self.assertFalse(order_ok.partner_id.last_notification_date)

        # opt-out partner remains unchanged
        order_opt_out.partner_id.invalidate_recordset()
        self.assertTrue(order_opt_out.partner_id.client_notified)
        self.assertTrue(order_opt_out.partner_id.last_notification_date)

        # not-notified partner remains unchanged
        order_not_notified.partner_id.invalidate_recordset()
        self.assertFalse(order_not_notified.partner_id.client_notified)
        self.assertFalse(order_not_notified.partner_id.last_notification_date)

    def test_multiple_orders_same_partner_only_one_write(self):
        """For multiple orders of the same partner, partner write() is called once."""
        partner = self.Partner.create(
            {
                "name": "Repeated Customer",
                "client_notified": True,
                "purchase_notifications_enabled": True,
                "last_notification_date": date.today(),
            }
        )
        order_1 = self._make_order(partner)
        order_2 = self._make_order(partner)

        calls = {"count": 0}

        # Patch the model class (not the recordset)
        partner_model_class = self.Partner.__class__
        original_write = partner_model_class.write

        def write_spy(self_recordset, vals):
            # Count only writes on res.partner
            if getattr(self_recordset, "_name", None) == "res.partner":
                calls["count"] += 1
            return original_write(self_recordset, vals)

        # Patch partner write and perform the reset on both orders
        with patch.object(partner_model_class, "write", new=write_spy):
            # pylint: disable=protected-access
            order_1._reset_partner_notification(order_1 | order_2)

        # Exactly one partner write must have happened
        self.assertEqual(calls["count"], 1)

        # And flags are reset
        partner.invalidate_recordset()
        self.assertFalse(partner.client_notified)
        self.assertFalse(partner.last_notification_date)
