import json
from odoo import models, fields, api

class VerifactiLog(models.Model):
    _name = 'verifacti.log'
    _description = 'Verifacti Transaction Log'
    _order = 'create_date desc'

    invoice_id = fields.Many2one(
        'account.invoice',
        string='Invoice',
        required=True,
        ondelete='cascade'
    )
    state = fields.Selection([
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('error', 'Error')
    ], string='State', default='pending', required=True)

    request_data = fields.Text(
        string='Request Data',
        readonly=True
    )
    response_data = fields.Text(
        string='Response Data',
        readonly=True
    )
    error_message = fields.Text(
        string='Error Message',
        readonly=True
    )
    verifacti_id = fields.Char(
        string='Verifacti ID',
        readonly=True,
        index=True
    )
    qr_code = fields.Binary(
        string='QR Code',
        readonly=True
    )
    sent_date = fields.Datetime(
        string='Sent Date',
        readonly=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='invoice_id.company_id',
        store=True
    )

    def process_pending(self):
        """Process pending logs - called by cron"""
        pending_logs = self.search([('state', '=', 'pending')], limit=50)
        for log in pending_logs:
            log.send_to_verifacti()

    def send_to_verifacti(self):
        """Send invoice data to Verifacti"""
        self.ensure_one()

        if self.state != 'pending':
            return

        try:
            api_client = self.env['verifacti.api.client']
            company = self.company_id

            if not company.verifacti_active or not company.verifacti_api_key:
                self.write({
                    'state': 'error',
                    'error_message': 'Verifacti is not configured or not active for this company'
                })
                return

            # Send invoice to Verifacti
            result = api_client.send_invoice(company, self.invoice_id)

            if result.get('success'):
                self.write({
                    'state': 'accepted',
                    'sent_date': fields.Datetime.now(),
                    'verifacti_id': result.get('id'),
                    'qr_code': result.get('qr_code'),
                    'response_data': json.dumps(result.get('response', {}))
                })

                # Update invoice with QR code and URL
                verifacti_url = result.get('url', '')
                # If no URL in response, construct it from ID
                if not verifacti_url and result.get('id'):
                    verifacti_url = 'https://verifacti.com/invoice/{}'.format(result.get('id'))

                self.invoice_id.write({
                    'verifacti_state': 'sent',
                    'verifacti_qr_code': result.get('qr_code'),
                    'verifacti_id': result.get('id'),
                    'verifacti_url': verifacti_url
                })
            else:
                self.write({
                    'state': 'rejected' if result.get('rejected') else 'error',
                    'error_message': result.get('error', 'Unknown error'),
                    'response_data': json.dumps(result.get('response', {}))
                })

                self.invoice_id.write({
                    'verifacti_state': 'error'
                })

        except Exception as e:
            self.write({
                'state': 'error',
                'error_message': str(e)
            })
            self.invoice_id.write({
                'verifacti_state': 'error'
            })
