# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
from odoo import models, fields


class VerifactiLog(models.Model):
    _name = 'verifacti.log'
    _description = 'Verifacti Transaction Log'
    _order = 'create_date desc'

    invoice_id = fields.Many2one(
        'account.invoice',
        string='Invoice',
        required=True,
        ondelete='cascade',
    )

    state = fields.Selection([
            ('pending', 'Pending'),
            ('sent', 'Sent'),
            ('accepted', 'Accepted'),
            ('rejected', 'Rejected'),
            ('error', 'Error')
        ],
        string='Status',
        default='pending',
        required=True,
    )

    request_data = fields.Text(
        string='Request Data',
        readonly=True,
    )

    response_data = fields.Text(
        string='Response Data',
        readonly=True,
    )

    error_message = fields.Text(
        string='Error Message',
        readonly=True,
    )

    verifacti_id = fields.Char(
        string='Verifacti ID',
        readonly=True,
        index=True,
    )

    qr_code = fields.Binary(
        string='QR Code',
        readonly=True,
    )

    sent_date = fields.Datetime(
        string='Sent Date',
        readonly=True,
    )

    last_check_date = fields.Datetime(
        string='Last Check Date',
        readonly=True,
        help='Last time the status was checked with Verifacti API',
    )

    retry_count = fields.Integer(
        string='Retry Count',
        default=0,
        help='Number of times status check has been retried',
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='invoice_id.company_id',
        store=True,
    )

    def check_pending_status(self):
        """Check status of sent invoices - called by cron to update QR and final status"""

        sent_logs = self.search([
            ('state', '=', 'sent'),
            ('retry_count', '<', 10)
        ])

        for log in sent_logs:
            try:
                log._check_invoice_status()
            except Exception:
                pass

    def _check_invoice_status(self):
        """Check the current status of an invoice with Verifacti API"""

        self.ensure_one()
        import logging
        _logger = logging.getLogger(__name__)

        if not self.verifacti_id:
            return

        api_client = self.env['verifacti.api.client']
        company = self.company_id

        if not company.verifacti_active or not company.verifacti_api_key:
            return

        try:
            result = api_client.check_invoice_status(company, self.verifacti_id)

            values = {}
            values['last_check_date'] = fields.Datetime.now()
            count = (self.retry_count or 0) if isinstance(self.retry_count, int) else 0
            values['retry_count'] = count + 1
            self.write(values)


            if result.get('success'):
                status = result.get('status', 'sent')
                response = result.get('response', {})
                error_msg = response.get('error_message') or response.get('error_code') or result.get('error')

                # Map status to verifacti_state
                if status == 'accepted':
                    verifacti_state = 'sent'
                elif status == 'rejected':
                    verifacti_state = 'error'
                elif status in ['sent', 'processing']:
                    verifacti_state = 'pending'
                else:
                    verifacti_state = 'pending'

                incident = bool(error_msg)

                log_values = {
                    'response_data': json.dumps(response, indent=2),
                    'last_check_date': fields.Datetime.now(),
                    'retry_count': count + 1
                }
                if status == 'accepted':
                    log_values['state'] = 'accepted'
                    log_values['qr_code'] = result.get('qr_code')
                elif status == 'rejected':
                    log_values['state'] = 'rejected'
                    log_values['error_message'] = error_msg
                self.write(log_values)

                # Update invoice
                invoice_values = {
                    'verifacti_state': verifacti_state,
                    'verifacti_incident': incident,
                }
                if status == 'accepted':
                    invoice_values['verifacti_qr_code'] = result.get('qr_code')
                    invoice_values['verifacti_url'] = result.get('url', '')
                self.invoice_id.write(invoice_values)

                if status == 'rejected':
                    _logger.warning('Invoice %s rejected by Verifacti: %s', self.invoice_id.number, error_msg)
                elif status == 'accepted':
                    _logger.info('Invoice %s accepted by Verifacti', self.invoice_id.number)
                elif status in ['sent', 'processing']:
                    _logger.info('Invoice %s still processing (retry %d)', self.invoice_id.number, self.retry_count)

            else:
                error_msg = result.get('error', 'Error checking invoice status')
                _logger.error('Error checking status for invoice %s: %s', self.invoice_id.number, error_msg)

                count = (self.retry_count or 0) if isinstance(self.retry_count, int) else 0
                if count >= 10:
                    self.write({
                        'state': 'error',
                        'error_message': 'Max retries exceeded. Last error: {}'.format(error_msg)
                    })
                    values = {}
                    values['verifacti_state'] = 'error'
                    self.invoice_id.write(values)

        except Exception as e:
            _logger.error('Exception checking status for log %s: %s', self.id, str(e))
            count = (self.retry_count or 0) if isinstance(self.retry_count, int) else 0
            if count >= 10:
                self.write({
                    'state': 'error',
                    'error_message': 'Max retries exceeded. Last exception: {}'.format(str(e))
                })
                values = {}
                values['verifacti_state'] = 'error'
                self.invoice_id.write(values)

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

            result = api_client.send_invoice(company, self.invoice_id)

            if result.get('success'):
                import logging
                _logger = logging.getLogger(__name__)

                verifacti_id = result.get('id')
                status = result.get('status', 'sent')

                if status == 'accepted' and result.get('qr_code'):
                    self.write({
                        'state': 'accepted',
                        'sent_date': fields.Datetime.now(),
                        'verifacti_id': verifacti_id,
                        'qr_code': result.get('qr_code'),
                        'response_data': json.dumps(result.get('response', {}), indent=2),
                        'last_check_date': fields.Datetime.now()
                    })

                    verifacti_url = result.get('url', '')
                    if not verifacti_url and verifacti_id:
                        verifacti_url = 'https://verifacti.com/invoice/{}'.format(verifacti_id)

                    values = {}
                    values['verifacti_state'] = 'sent'
                    values['verifacti_qr_code'] = result.get('qr_code')
                    values['verifacti_id'] = verifacti_id
                    values['verifacti_url'] = verifacti_url
                    self.invoice_id.write(values)

                else:
                    self.write({
                        'state': 'sent',
                        'sent_date': fields.Datetime.now(),
                        'verifacti_id': verifacti_id,
                        'response_data': json.dumps(result.get('response', {}), indent=2),
                        'last_check_date': fields.Datetime.now()
                    })

                    values = {}
                    values['verifacti_state'] = 'pending'
                    self.invoice_id.write(values)

                    _logger.info('Invoice %s sent to Verifacti, waiting for confirmation', self.invoice_id.number)
            else:
                error_msg = result.get('error', 'Unknown error')
                self.write({
                    'state': 'rejected' if result.get('rejected') else 'error',
                    'error_message': error_msg,
                    'response_data': json.dumps(result.get('response', {}), indent=2)
                })

                values = {}
                values['verifacti_state'] = 'error'
                self.invoice_id.write(values)

        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error('Exception sending invoice %s: %s', self.invoice_id.number, str(e))

            self.write({
                'state': 'error',
                'error_message': str(e)
            })

            values = {}
            values['verifacti_state'] = 'error'
            self.invoice_id.write(values)
