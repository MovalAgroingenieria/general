from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class VerifactiConfig(models.Model):
    _name = 'verifacti.config'
    _description = 'Verifacti Configuration'
    _rec_name = 'company_id'

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    api_key = fields.Char(
        string='API Key',
        required=True,
        help='API Key provided by Verifacti'
    )
    api_url = fields.Char(
        string='API URL',
        default='https://api.verifacti.com',
        required=True,
        help='Verifacti API endpoint URL'
    )
    nif_api_url = fields.Char(
        string='NIF API URL',
        default='https://nifs.verifacti.com',
        required=True,
        help='Verifacti NIF API endpoint URL'
    )
    is_production = fields.Boolean(
        string='Production Environment',
        default=False,
        help='Check if this is a production environment'
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )
    auto_send = fields.Boolean(
        string='Auto Send on Validation',
        default=True,
        help='Automatically send invoices to Verifacti when validated'
    )

    @api.constrains('company_id')
    def _check_unique_company(self):
        for record in self:
            if self.search_count([
                ('company_id', '=', record.company_id.id),
                ('id', '!=', record.id)
            ]) > 0:
                raise ValidationError(_('Only one Verifacti configuration per company is allowed.'))

    def get_config(self, company_id=None):
        """Get active configuration for the company"""
        if not company_id:
            company_id = self.env.company.id
        config = self.search([
            ('company_id', '=', company_id),
            ('active', '=', True)
        ], limit=1)
        return config
