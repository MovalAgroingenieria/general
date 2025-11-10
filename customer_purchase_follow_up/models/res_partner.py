# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# pylint: disable=protected-access
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    purchase_notifications_enabled = fields.Boolean(
        default=False,
        help="Activate to receive notifications when this customer hasn't "
        "purchased in a while",
    )

    days_without_purchase_limit = fields.Integer(
        default=30,
        help="Maximum days without purchase before sending notification",
    )

    notification_users = fields.Many2many(
        "res.users",
        "partner_notification_users_rel",
        "partner_id",
        "user_id",
        help="Users who will receive notifications for this customer",
    )

    send_email_notification = fields.Boolean(
        default=False,
        help="Send notification by email",
    )

    create_crm_opportunity = fields.Boolean(
        default=False,
        help="Create an opportunity in CRM when notification is triggered",
    )

    last_purchase_date = fields.Date(
        compute="_compute_last_purchase_date",
        store=True,
        help="Date of the last confirmed purchase order",
    )

    days_since_last_purchase = fields.Integer(
        compute="_compute_days_since_last_purchase",
        store=False,
        help="Number of days since the last purchase",
    )

    client_notified = fields.Boolean(
        default=False,
        help="Indicates if the client has already been notified about "
        "lack of recent purchases",
    )

    last_notification_date = fields.Datetime(
        help="Date when the last notification was sent"
    )

    @api.depends("sale_order_ids", "sale_order_ids.state", "sale_order_ids.date_order")
    def _compute_last_purchase_date(self):
        """Compute the date of the last confirmed sale order."""
        for partner in self:
            old_last_purchase_date = partner.last_purchase_date

            # Filter confirmed orders and sort by date (newest first)
            confirmed_orders = partner.sale_order_ids.filtered(
                lambda o: o.state in ["sale", "done"]
            ).sorted("date_order", reverse=True)

            if confirmed_orders:
                last_order = confirmed_orders[0]
                partner.last_purchase_date = last_order.date_order.date()

                # If there's a new purchase after being notified,
                # reset notification status
                if (
                    partner.client_notified
                    and old_last_purchase_date
                    and partner.last_purchase_date > old_last_purchase_date
                ):
                    partner.client_notified = False
                    partner.last_notification_date = False
            else:
                partner.last_purchase_date = False

    @api.depends("last_purchase_date")
    def _compute_days_since_last_purchase(self):
        """Compute the number of days since last purchase."""
        today = fields.Date.today()
        for partner in self:
            if partner.last_purchase_date:
                delta = today - partner.last_purchase_date
                partner.days_since_last_purchase = delta.days
            else:
                partner.days_since_last_purchase = 0

    def action_send_manual_notification(self):
        """Manual action to send notification for this partner."""
        self.ensure_one()
        if not self.purchase_notifications_enabled:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": self.env._("Warning"),
                    "message": self.env._(
                        "Purchase notifications are not enabled for this customer."
                    ),
                    "type": "warning",
                    "sticky": False,
                },
            }

        self._send_purchase_notification(manual=True)

        # Refresh fields and view
        self._refresh_purchase_fields()

        return {
            "type": "ir.actions.act_window",
            "res_model": "res.partner",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
            "context": {
                "notification_message": self.env._("Notification sent successfully."),
            },
        }

    def _send_purchase_notification(self, manual=False):
        """Send notification for customers without recent purchases."""
        for partner in self:
            if not partner.purchase_notifications_enabled:
                continue

            # Skip if not manual and already notified
            if not manual and partner.client_notified:
                continue

            days_since_purchase = partner.days_since_last_purchase
            days_limit = partner.days_without_purchase_limit

            # Skip if not manual and within purchase limit
            if not manual and days_since_purchase <= days_limit:
                continue

            # Send email notification if configured
            if partner.send_email_notification and partner.notification_users:
                partner._send_email_notification()

            # Create CRM opportunity if configured
            if partner.create_crm_opportunity:
                partner._create_crm_opportunity()

            # Mark as notified and update timestamp
            partner.write(
                {
                    "client_notified": True,
                    "last_notification_date": fields.Datetime.now(),
                }
            )

            # Force immediate update of computed fields
            partner._refresh_purchase_fields()

            _logger.info(
                "Purchase notification sent for partner %s (ID: %s)",
                partner.name,
                partner.id,
            )

    def _send_email_notification(self):
        """Send email notification to configured users."""
        self.ensure_one()
        template = self.env.ref(
            "customer_purchase_follow_up.mail_template_purchase_notification",
            raise_if_not_found=False,
        )

        if not template:
            _logger.error("Email template not found for purchase notifications")
            return

        for user in self.notification_users:
            if user.email:
                # Create specific context for each user
                email_context = {
                    "recipient_user": user,
                    "partner_name": self.name,
                    "days_since_purchase": self.days_since_last_purchase,
                    "last_purchase_date": self.last_purchase_date,
                }

                # Send email with specific context
                template.with_context(**email_context).send_mail(
                    self.id,
                    force_send=True,
                    email_values={
                        "email_to": user.email,
                    },
                )

                _logger.info(
                    "Email notification sent to %s for partner %s",
                    user.email,
                    self.name,
                )

    def _create_crm_opportunity(self):
        """Create a CRM opportunity for follow-up."""
        self.ensure_one()

        # Find a sales team that uses opportunities
        sales_team = self.env["crm.team"].search(
            [("use_opportunities", "=", True)], limit=1
        )

        # Prepare opportunity values
        name = self.env._("Follow-up: Customer without recent purchases - %s")
        description_template = self.env._(
            "This opportunity was created automatically because the "
            "customer has not made purchases for %(days)d days. "
            "Last purchase date: %(date)s"
        )
        opportunity_vals = {
            "name": name % self.name,
            "partner_id": self.id,
            "type": "opportunity",
            "description": description_template
            % {
                "days": self.days_since_last_purchase,
                "date": self.last_purchase_date or self.env._("Never"),
            },
            "team_id": sales_team.id if sales_team else False,
        }

        # Assign to first notification user if available
        if self.notification_users:
            opportunity_vals["user_id"] = self.notification_users[0].id

        opportunity = self.env["crm.lead"].create(opportunity_vals)

        _logger.info(
            "CRM opportunity created for partner %s (ID: %s), opportunity ID: %s",
            self.name,
            self.id,
            opportunity.id,
        )

    @api.model
    def _cron_check_purchase_notifications(self):
        """Cron job to check and send notifications for
        customers without recent purchases."""
        _logger.info("Starting purchase notifications check")

        # Find partners with notifications enabled and not yet notified
        partners = self.search(
            [
                ("purchase_notifications_enabled", "=", True),
                ("client_notified", "=", False),
                ("is_company", "=", True),
            ]
        )

        notification_count = 0
        for partner in partners:
            days_limit = partner.days_without_purchase_limit
            if partner.days_since_last_purchase > days_limit:
                partner._send_purchase_notification()
                notification_count += 1

        _logger.info(
            "Purchase notifications check completed. %d notifications sent",
            notification_count,
        )

    def _refresh_purchase_fields(self):
        """Refresh purchase-related computed fields."""
        self.ensure_one()

        # Invalidate cache for this record
        self.invalidate_recordset()

        # Refresh specific computed fields
        self._compute_last_purchase_date()
        self._compute_days_since_last_purchase()

        # Force write to trigger updates
        self.env.cr.execute(
            "SELECT write_date FROM res_partner WHERE id = %s", (self.id,)
        )

        # Flush to ensure persistence
        self.flush_recordset()

    def reset_notification_status(self):
        """Reset notification status to allow sending notifications again."""
        self.write(
            {
                "client_notified": False,
                "last_notification_date": False,
            }
        )

        # Refresh fields and view
        self._refresh_purchase_fields()

        return {
            "type": "ir.actions.act_window",
            "res_model": "res.partner",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
            "context": {
                "notification_message": self.env._(
                    "Notification status reset successfully."
                ),
            },
        }

    def write(self, vals):
        """Override write to reset notification when new orders are confirmed."""
        result = super().write(vals)

        # If sale orders are updated, check if notification should be reset
        if "sale_order_ids" in vals:
            for partner in self:
                if partner.client_notified and partner.last_purchase_date:
                    # Recompute to check for new purchases
                    partner._compute_last_purchase_date()

        return result
