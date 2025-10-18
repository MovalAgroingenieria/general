# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    verifacti_api_key = fields.Char(
        string='Verifacti API Key',
        help='API Key provided by Verifacti'
    )
    verifacti_api_url = fields.Char(
        string='Verifacti API URL',
        default='https://api.verifacti.com',
        help='Verifacti API endpoint URL'
    )
    verifacti_nif_api_url = fields.Char(
        string='NIF API URL',
        default='https://nifs.verifacti.com',
        help='Verifacti NIF API endpoint URL'
    )
    verifacti_active = fields.Boolean(
        string='Enable Verifacti',
        default=False,
        help='Enable Verifacti integration for this company'
    )

