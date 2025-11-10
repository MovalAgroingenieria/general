# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# We intentionally access private helpers in tests for coverage.
# pylint: disable=protected-access, invalid-name

from unittest.mock import Mock, patch

from dateutil.relativedelta import relativedelta
from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPartnerPurchaseFollowUp(TransactionCase):
    """Tests for ResPartner purchase follow-up logic."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.Partner = cls.env["res.partner"]
        cls.User = cls.env["res.users"]
        cls.Team = cls.env["crm.team"]
        cls.Lead = cls.env["crm.lead"]
        cls.Product = cls.env["product.product"]
        cls.SaleOrder = cls.env["sale.order"]
        cls.SaleOrderLine = cls.env["sale.order.line"]

        # Minimal product to confirm orders
        cls.product = cls.Product.create(
            {"name": "Test Service", "type": "service", "list_price": 100.0}
        )

        # Sales team that supports opportunities for CRM tests
        cls.team = cls.Team.create({"name": "Test Team", "use_opportunities": True})

        # Notification user with an email
        cls.user = cls.User.create(
            {
                "name": "Notify User",
                "login": "notify_user@example.com",
                "email": "notify_user@example.com",
            }
        )

        # Helper partners
        cls.partner_enabled = cls.Partner.create(
            {
                "name": "Enabled Partner",
                "purchase_notifications_enabled": True,
                "days_without_purchase_limit": 30,
                "send_email_notification": True,
                "create_crm_opportunity": True,
                "notification_users": [(6, 0, [cls.user.id])],
                "is_company": True,
            }
        )
        cls.partner_disabled = cls.Partner.create(
            {
                "name": "Disabled Partner",
                "purchase_notifications_enabled": False,
                "is_company": True,
            }
        )

    # -------------------------
    # Utility helpers
    # -------------------------
    def _make_order(
        self,
        partner,
        days_ago=0,
        state="sale",
    ):
        """Create a sale order and a line; set date_order and state."""
        order = self.SaleOrder.create({"partner_id": partner.id})
        self.SaleOrderLine.create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "product_uom_qty": 1.0,
                "price_unit": 100.0,
                "name": "Test line",
            }
        )
        # Set order date in the past if needed
        order.write(
            {
                "date_order": fields.Datetime.to_string(
                    fields.Datetime.now() - relativedelta(days=days_ago)
                )
            }
        )
        # Move to target state (bypass full sale flow for test speed)
        order.write({"state": state})
        return order

    # -------------------------
    # Compute fields
    # -------------------------
    def test_compute_last_purchase_date_updates_and_resets(self):
        """When a newer confirmed order exists, last_purchase_date updates and
        notification flags are reset if previously notified."""
        p = self.partner_enabled.copy()
        # Initial purchase 20 days ago
        self._make_order(p, days_ago=20, state="sale")
        p._refresh_purchase_fields()
        self.assertTrue(p.last_purchase_date)
        # Simulate previously notified status
        p.write(
            {"client_notified": True, "last_notification_date": fields.Datetime.now()}
        )

        # Newer purchase 1 day ago -> compute should reset notification flags
        self._make_order(p, days_ago=1, state="sale")
        p._refresh_purchase_fields()

        self.assertTrue(p.last_purchase_date)
        self.assertFalse(p.client_notified)
        self.assertFalse(p.last_notification_date)

    def test_compute_days_since_last_purchase(self):
        """days_since_last_purchase equals the delta from today."""
        p = self.partner_enabled.copy()
        target_days = 7
        # Make sure there is a purchase exactly target_days ago
        self._make_order(p, days_ago=target_days, state="sale")
        p._refresh_purchase_fields()
        self.assertEqual(p.days_since_last_purchase, target_days)

        # If no purchases, computed value is 0
        q = self.partner_enabled.copy()
        q._refresh_purchase_fields()
        self.assertEqual(q.days_since_last_purchase, 0)

    # -------------------------
    # Manual action
    # -------------------------
    def test_action_send_manual_notification_disabled_returns_warning(self):
        """Manual action returns UI warning when notifications are disabled."""
        action = self.partner_disabled.action_send_manual_notification()
        self.assertEqual(action.get("type"), "ir.actions.client")
        self.assertEqual(action.get("tag"), "display_notification")
        self.assertEqual(action.get("params", {}).get("type"), "warning")

    def test_action_send_manual_notification_enabled_executes(self):
        """Manual action triggers notification and returns act_window."""
        p = self.partner_enabled.copy()
        # Ensure the partner is beyond the limit
        self._make_order(p, days_ago=40, state="sale")
        p._refresh_purchase_fields()

        with patch.object(
            type(p), "_send_purchase_notification"
        ) as send_mock, patch.object(
            type(p), "_refresh_purchase_fields"
        ) as refresh_mock:
            action = p.action_send_manual_notification()

        send_mock.assert_called_once()
        refresh_mock.assert_called_once()
        self.assertEqual(action.get("type"), "ir.actions.act_window")
        self.assertEqual(action.get("res_model"), "res.partner")
        self.assertEqual(action.get("res_id"), p.id)

    # -------------------------
    # Notification sending
    # -------------------------
    def test_send_purchase_notification_marks_notified_and_emails(self):
        """_send_purchase_notification marks notified, timestamps, and sends emails.

        Focus on the email path: disable CRM to avoid external dependencies.
        """
        p = self.partner_enabled.copy(
            {
                "create_crm_opportunity": False,  # avoid CRM internals
                "send_email_notification": True,
                "notification_users": [(6, 0, [self.user.id])],
            }
        )
        # Older than limit -> should trigger (limit=30)
        self._make_order(p, days_ago=45, state="sale")
        p._refresh_purchase_fields()

        # Fake mail template lookup and sending
        fake_template = Mock()
        # Important: make with_context return the same mock so send_mail is tracked here
        fake_template.with_context.return_value = fake_template

        def fake_ref(xmlid, raise_if_not_found=False):
            if (
                xmlid
                == "customer_purchase_follow_up.mail_template_purchase_notification"
            ):
                return fake_template
            if raise_if_not_found:
                raise ValueError("not found")
            return None

        with patch.object(type(p.env), "ref", side_effect=fake_ref):
            p._send_purchase_notification(manual=False)

        p.invalidate_recordset()
        self.assertTrue(p.client_notified)
        self.assertTrue(p.last_notification_date)
        # Either of these two assertions is fine now:
        fake_template.send_mail.assert_called()  # because with_context
        # returns fake_template
        # fake_template.with_context.return_value.send_mail.assert_called()

    def test_send_purchase_notification_skips_when_within_limit_and_not_manual(self):
        """When within the limit and not manual, notification is skipped."""
        p = self.partner_enabled.copy()
        # Within limit: 5 days ago (limit=30)
        self._make_order(p, days_ago=5, state="sale")
        p._refresh_purchase_fields()

        with patch.object(
            type(p), "_send_email_notification"
        ) as email_mock, patch.object(type(p), "_create_crm_opportunity") as crm_mock:
            p._send_purchase_notification(manual=False)

        self.assertFalse(p.client_notified)
        self.assertFalse(email_mock.called)
        self.assertFalse(crm_mock.called)

    def test_send_purchase_notification_creates_crm_lead(self):
        """When configured, the CRM opportunity creation hook is invoked.

        We mock the helper instead of relying on CRM internals (sales_team, mail).
        """
        p = self.partner_enabled.copy(
            {
                "create_crm_opportunity": True,
                "send_email_notification": False,  # isolate CRM path
                "notification_users": [(6, 0, [])],
            }
        )
        # Exceed the limit so notification would trigger
        self._make_order(p, days_ago=50, state="sale")
        p._refresh_purchase_fields()

        with patch.object(type(p), "_create_crm_opportunity") as crm_mock:
            p._send_purchase_notification(manual=False)

        crm_mock.assert_called_once_with()
        p.invalidate_recordset()
        self.assertTrue(p.client_notified)

    # -------------------------
    # Cron job
    # -------------------------
    def test_cron_only_notifies_over_limit(self):
        """Cron only notifies partners exceeding the days limit
        (no email/CRM side effects)."""
        p_over = self.partner_enabled.copy(
            {
                "name": "Over Limit",
                "days_without_purchase_limit": 10,
                "send_email_notification": False,  # avoid mail template rendering
                "create_crm_opportunity": False,  # avoid CRM side effects
                "notification_users": [(6, 0, [])],
            }
        )
        p_under = self.partner_enabled.copy(
            {
                "name": "Under Limit",
                "days_without_purchase_limit": 60,
                "send_email_notification": False,
                "create_crm_opportunity": False,
                "notification_users": [(6, 0, [])],
            }
        )

        # Purchases: 30 days ago for p_over, 5 days ago for p_under
        self._make_order(p_over, days_ago=30, state="sale")
        self._make_order(p_under, days_ago=5, state="sale")
        p_over._refresh_purchase_fields()
        p_under._refresh_purchase_fields()

        self.Partner._cron_check_purchase_notifications()

        p_over.invalidate_recordset()
        p_under.invalidate_recordset()
        self.assertTrue(p_over.client_notified)
        self.assertFalse(p_under.client_notified)

    # -------------------------
    # Reset action
    # -------------------------
    def test_reset_notification_status_action_and_effect(self):
        """reset_notification_status clears flags and returns a form action."""
        p = self.partner_enabled.copy()
        p.write(
            {
                "client_notified": True,
                "last_notification_date": fields.Datetime.now(),
            }
        )

        action = p.reset_notification_status()
        p.invalidate_recordset()

        self.assertFalse(p.client_notified)
        self.assertFalse(p.last_notification_date)
        self.assertEqual(action.get("type"), "ir.actions.act_window")
        self.assertEqual(action.get("res_model"), "res.partner")
        self.assertEqual(action.get("res_id"), p.id)

    # -------------------------
    # write() override behavior
    # -------------------------
    def test_write_on_sale_order_ids_triggers_recompute_and_may_reset(self):
        """When sale_order_ids are updated, compute may reset notified flags.

        This test focuses on the write() hook behavior, not on email/CRM side effects.
        We disable email and CRM to avoid rendering real mail templates (which may
        depend on a dynamic 'lang' expression like ${object.lang}).
        """
        p = self.partner_enabled.copy(
            {
                "send_email_notification": False,  # avoid hitting mail templates
                "create_crm_opportunity": False,  # avoid CRM side effects
                "notification_users": [(6, 0, [])],  # ensure no recipients
            }
        )

        # First purchase 40 days ago -> partner qualifies for notification
        self._make_order(p, days_ago=40, state="sale")
        p._refresh_purchase_fields()
        # Manually mark as notified to emulate previous notification having been sent
        p._send_purchase_notification(manual=False)
        self.assertTrue(p.client_notified)

        # New purchase today should reset flags via partner.write() hook
        new_order = self._make_order(p, days_ago=0, state="sale")
        # Update One2many to trigger partner.write() and the recompute path
        p.write({"sale_order_ids": [(4, new_order.id)]})

        p.invalidate_recordset()
        self.assertFalse(p.client_notified)
        self.assertFalse(p.last_notification_date)
