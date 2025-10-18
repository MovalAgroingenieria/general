# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    verifacti_api_key = fields.Char(
        string='Verifacti API Key',
        related='company_id.verifacti_api_key',
        help='API Key provided by Verifacti'
    )
    verifacti_api_url = fields.Char(
        string='Verifacti API URL',
        related='company_id.verifacti_api_url',
        help='Verifacti API endpoint URL'
    )
    verifacti_nif_api_url = fields.Char(
        string='NIF API URL',
        related='company_id.verifacti_nif_api_url',
        help='Verifacti NIF API endpoint URL'
    )
    verifacti_active = fields.Boolean(
        string='Enable Verifacti',
        related='company_id.verifacti_active',
        help='Enable Verifacti integration for this company'
    )
