# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def _message_auto_subscribe_notify(self, partner_ids):
        """
        Override to prevent automatic notification when user_id is assigned.
        
        The default behavior sends a notification to all followers (including
        suppliers) when a user is assigned to an invoice. This override
        disables that notification for account.invoice records.
        """
        # Log that the method is being called but notification is suppressed
        _logger.info(
            "Invoice %s: Auto-subscribe notification suppressed for %d partners",
            self.mapped('number') or self.ids,
            len(partner_ids) if partner_ids else 0
        )
        # Do not send automatic assignment notifications for invoices
        return
