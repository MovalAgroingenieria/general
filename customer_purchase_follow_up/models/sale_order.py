# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _reset_partner_notification(self, orders):
        """Reset notification flags on related partners for the given orders."""
        # Keep only orders whose partners are currently
        # notified and have the option enabled
        orders = orders.filtered(
            lambda o: o.partner_id.client_notified
            and o.partner_id.purchase_notifications_enabled
        )
        if not orders:
            return
        # Avoid writing the same partner multiple times
        partners = orders.mapped("partner_id")
        partners.write(
            {
                "client_notified": False,
                "last_notification_date": False,
            }
        )
        for o in orders:
            _logger.info(
                "Reset notification status for partner %s due to order %s",
                o.partner_id.name,
                o.name,
            )

    def action_confirm(self):
        """Reset partner notification when the order is confirmed.

        In v18, `action_confirm` still transitions the state to 'sale'. To avoid
        triggering a duplicate reset from `write` (due to the state change),
        we pass a context flag while calling `super()`.
        """
        # Pass context to ensure any internal write(state='sale') inherits the skip flag
        result = super(
            SaleOrder, self.with_context(skip_reset_partner_notification=True)
        ).action_confirm()

        # After confirmation, apply the notification reset if applicable
        self._reset_partner_notification(self)
        return result

    def write(self, vals):
        """Override write to react to explicit state changes to 'sale' or 'done'."""
        result = super().write(vals)

        # If we came from action_confirm, skip a duplicate reset here
        if self.env.context.get("skip_reset_partner_notification"):
            return result

        # If the state was explicitly changed to 'sale' or 'done', reset notifications
        if "state" in vals and vals["state"] in ("sale", "done"):
            self._reset_partner_notification(self)

        return result
