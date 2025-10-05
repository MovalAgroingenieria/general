# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        """Override to reset partner notification when order is confirmed."""
        result = super(SaleOrder, self).action_confirm()

        for order in self:
            partner = order.partner_id
            if (partner.client_notified and
                    partner.purchase_notifications_enabled):
                # Nueva compra confirmada - resetear estado de notificación
                partner.write({
                    'client_notified': False,
                    'last_notification_date': False,
                })
                _logger.info(
                    'Reset notification status for partner %s due to new '
                    'confirmed order %s',
                    partner.name, order.name
                )

        return result

    def write(self, vals):
        """Override write to detect state changes to 'sale'."""
        result = super(SaleOrder, self).write(vals)

        # Si cambia el estado a 'sale' o 'done'
        if 'state' in vals and vals['state'] in ['sale', 'done']:
            for order in self:
                partner = order.partner_id
                if (partner.client_notified and
                        partner.purchase_notifications_enabled):
                    # Nueva compra - resetear notificación
                    partner.write({
                        'client_notified': False,
                        'last_notification_date': False,
                    })
                    _logger.info(
                        'Reset notification status for partner %s due to '
                        'order state change to %s',
                        partner.name, vals['state']
                    )

        return result
