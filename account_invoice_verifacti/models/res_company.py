# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    verifacti_api_key = fields.Char(
        string='Verifacti API Key',
        help='API Key provided by Verifacti',
    )

    verifacti_api_url = fields.Char(
        string='Verifacti API URL',
        default='https://api.verifacti.com',
        help='Verifacti API endpoint URL',
    )

    verifacti_active = fields.Boolean(
        string='Enable Verifacti',
        default=False,
        help='Enable Verifacti integration for this company',
    )

    verifacti_notification_user_ids = fields.Many2many(
        'res.users',
        'verifacti_notification_user_rel',
        'company_id',
        'user_id',
        string='Notification Recipients',
        help='Users who will receive notifications when an invoice is rejected by Verifacti',
    )

    verifacti_notify_on_rejection = fields.Boolean(
        string='Send Notifications on Rejection',
        default=True,
        help='Enable notifications when invoices are rejected by Verifacti',
    )

    verifacti_regime_code = fields.Char(
        string='Regime Code',
        help='Default VAT regime code for this company',
    )

    verifacti_validate_recipient = fields.Boolean(
        string='Validate Recipient',
        default=True,
        help='Validate recipient data when sending invoices to Verifacti',
    )


