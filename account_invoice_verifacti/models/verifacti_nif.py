from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import requests
import json
from datetime import datetime

class VerifactiNIF(models.Model):
    _name = 'verifacti.nif'
    _description = 'Verifacti NIF Management'
    _rec_name = 'nif'

    nif = fields.Char(
        string='NIF',
        required=True,
        index=True
    )
    name = fields.Char(
        string='Name',
        required=True
    )
    country_code = fields.Char(
        string='Country Code',
        default='ES',
        required=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('validated', 'Validated'),
        ('error', 'Error')
    ], string='State', default='draft')

    verifacti_id = fields.Char(
        string='Verifacti ID',
        readonly=True
    )
    validation_date = fields.Datetime(
        string='Validation Date',
        readonly=True
    )
    error_message = fields.Text(
        string='Error Message',
        readonly=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )

    @api.constrains('nif')
    def _check_unique_nif(self):
        for record in self:
            if self.env['verifacti.nif'].search_count([
                ('nif', '=', record.nif),
                ('company_id', '=', record.company_id.id),
                ('id', '!=', record.id)
            ]) > 0:
                raise ValidationError(_('NIF already exists for this company.'))

    def action_validate_nif(self):
        """Validate NIF with Verifacti API"""
        self.ensure_one()
        if not self.company_id.verifacti_active or not self.company_id.verifacti_api_key:
            raise UserError(_('Verifacti is not configured or not active for this company.'))

        api_client = self.env['verifacti.api.client']
        try:
            result = api_client.validate_nif(
                self.company_id,
                self.nif,
                self.name,
                self.country_code
            )

            if result.get('success'):
                self.write({
                    'state': 'validated',
                    'verifacti_id': result.get('id'),
                    'validation_date': datetime.now(),
                    'error_message': False
                })
            else:
                self.write({
                    'state': 'error',
                    'error_message': result.get('error', _('Unknown error'))
                })
        except Exception as e:
            self.write({
                'state': 'error',
                'error_message': str(e)
            })
            raise UserError(_('Error validating NIF: %s') % str(e))

    def action_create_nif(self):
        """Create NIF in Verifacti"""
        self.ensure_one()
        if not self.company_id.verifacti_active or not self.company_id.verifacti_api_key:
            raise UserError(_('Verifacti is not configured or not active for this company.'))

        api_client = self.env['verifacti.api.client']
        try:
            result = api_client.create_nif(
                self.company_id,
                self.nif,
                self.name,
                self.country_code
            )

            if result.get('success'):
                self.write({
                    'state': 'validated',
                    'verifacti_id': result.get('id'),
                    'validation_date': datetime.now(),
                    'error_message': False
                })
            else:
                self.write({
                    'state': 'error',
                    'error_message': result.get('error', _('Unknown error'))
                })
        except Exception as e:
            self.write({
                'state': 'error',
                'error_message': str(e)
            })
            raise UserError(_('Error creating NIF: %s') % str(e))
