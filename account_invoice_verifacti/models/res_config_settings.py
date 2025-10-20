# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    verifacti_api_key = fields.Char(
        string='Verifacti API Key',
        related='company_id.verifacti_api_key',
        help='API Key provided by Verifacti',
    )

    verifacti_api_url = fields.Char(
        string='Verifacti API URL',
        related='company_id.verifacti_api_url',
        help='Verifacti API endpoint URL',
    )

    verifacti_active = fields.Boolean(
        string='Enable Verifacti',
        related='company_id.verifacti_active',
        help='Enable Verifacti integration for this company',
    )

    verifacti_notification_user_ids = fields.Many2many(
        string='Notification Recipients',
        related='company_id.verifacti_notification_user_ids',
    )

    verifacti_notify_on_rejection = fields.Boolean(
        string='Send Notifications on Rejection',
        related='company_id.verifacti_notify_on_rejection',
    )
