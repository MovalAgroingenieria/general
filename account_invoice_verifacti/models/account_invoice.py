# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json
from collections import OrderedDict

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    verifacti_state = fields.Selection([
        ('not_sent', 'Not Sent'),
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('error', 'Error')
    ], string='Verifacti State', default='not_sent', readonly=True, copy=False)

    verifacti_id = fields.Char(
        string='Verifacti ID',
        readonly=True,
        copy=False
    )
    verifacti_qr_code = fields.Binary(
        string='Verifacti QR Code',
        readonly=True,
        copy=False
    )
    verifacti_url = fields.Char(
        string='Verifacti URL',
        readonly=True,
        copy=False,
        help='URL to view invoice on Verifacti portal'
    )
    verifacti_log_ids = fields.One2many(
        'verifacti.log',
        'invoice_id',
        string='Verifacti Logs',
        readonly=True
    )
    verifacti_last_error = fields.Text(
        string='Last Error',
        compute='_compute_verifacti_last_error'
    )
    verifacti_journal_enabled = fields.Boolean(
        string='Journal has Verifacti enabled',
        related='journal_id.verifacti_enabled',
        readonly=True
    )

    @api.depends('verifacti_log_ids.error_message')
    def _compute_verifacti_last_error(self):
        for move in self:
            last_log = move.verifacti_log_ids.filtered(
                lambda l: l.state == 'error'
            ).sorted('create_date', reverse=True)[:1]
            move.verifacti_last_error = last_log.error_message if last_log else False

    @api.multi
    def action_invoice_open(self):
        """Override invoice validation to send to Verifacti when invoice is validated"""
        # Call parent method to change state to 'open'
        res = super(AccountInvoice, self).action_invoice_open()

        # Only process customer invoices with Verifacti enabled journal
        invoices_to_send = self.filtered(
            lambda inv: inv.type in ['out_invoice', 'out_refund'] and
                       inv.company_id.country_id.code == 'ES' and
                       inv.journal_id.verifacti_enabled
        )

        # Process each invoice individually and collect errors
        failed_invoices = []
        error_messages = []

        for invoice in invoices_to_send:
            if invoice.company_id.verifacti_active:
                try:
                    invoice._create_verifacti_log()
                except Exception as e:
                    # If Verifacti fails, revert this specific invoice to draft
                    invoice.action_invoice_cancel()
                    invoice.action_invoice_draft()
                    failed_invoices.append(invoice.number or invoice.name)
                    error_messages.append(str(e))

        # If any invoice failed, show error message
        if failed_invoices:
            error_msg = _('Las siguientes facturas no pudieron enviarse a Verifacti y han vuelto a borrador:\n\n')
            for inv_name in failed_invoices:
                error_msg += u'• %s\n' % inv_name
            raise UserError(error_msg)

        return res

    def _create_verifacti_log(self):
        """Create a pending log entry for Verifacti"""
        self.ensure_one()

        if self.verifacti_state in ['sent', 'pending']:
            return

        # Prepare invoice data for Verifacti
        invoice_data = self._prepare_verifacti_data()

        # Create log entry
        log = self.env['verifacti.log'].create({
            'invoice_id': self.id,
            'state': 'pending',
            'request_data': json.dumps(invoice_data, indent=2, ensure_ascii=False)
        })

        self.write({'verifacti_state': 'pending'})

        # Try to send immediately if possible
        log.send_to_verifacti()

        # Check if sending failed and revert to draft if so
        if log.state in ['error', 'rejected']:
            # Revert invoice to draft state
            self.action_invoice_cancel()
            self.action_invoice_draft()
            # Raise error to inform user
            error_msg = log.error_message or 'Error al enviar a Verifacti'
            from odoo.exceptions import UserError
            raise UserError(
                _('La factura no pudo ser validada porque falló el envío a Verifacti:\n\n%s\n\nLa factura ha vuelto a estado borrador.') % error_msg
            )

        return log

    def _prepare_verifacti_data(self):
        """Prepare invoice data for Verifacti API according to official documentation"""
        self.ensure_one()

        # Extract serie and numero from invoice number (e.g., "F/2025/0599" -> serie="F", numero="2025/0599")
        # If invoice has no serie, use the whole number
        invoice_number = self.number or self.name
        if '/' in invoice_number:
            parts = invoice_number.split('/', 1)
            serie = parts[0]
            numero = parts[1]
        else:
            serie = invoice_number[:10]  # Limit serie length
            numero = invoice_number

        # Convert date format from YYYY-MM-DD to DD-MM-YYYY for Verifacti
        fecha_expedicion = ''
        if self.date_invoice:
            # date_invoice is string in format YYYY-MM-DD
            parts = self.date_invoice.split('-')
            if len(parts) == 3:
                fecha_expedicion = '{}-{}-{}'.format(parts[2], parts[1], parts[0])

        # Get current date for fecha_expedicion if invoice date not set
        if not fecha_expedicion:
            today = fields.Date.today()
            parts = today.split('-')
            fecha_expedicion = '{}-{}-{}'.format(parts[2], parts[1], parts[0])

        # Group invoice lines by tax to create Verifacti lines
        # Use tax_line_ids which contains the computed tax amounts
        verifacti_lines = []

        if self.tax_line_ids:
            # Use computed tax lines from invoice
            for tax_line in self.tax_line_ids:
                line_dict = OrderedDict([
                    ('base_imponible', str(round(tax_line.base, 2))),
                    ('tipo_impositivo', str(round(tax_line.tax_id.amount, 2))),
                    ('cuota_repercutida', str(round(tax_line.amount, 2)))
                ])
                verifacti_lines.append(line_dict)
        else:
            # No taxes - create line with total as base and 0% tax
            line_dict = OrderedDict([
                ('base_imponible', str(round(self.amount_untaxed, 2))),
                ('tipo_impositivo', '0.0'),
                ('cuota_repercutida', '0.0')
            ])
            verifacti_lines.append(line_dict)

        # Clean NIF: Remove country prefix (ES, PT, FR, etc.)
        partner_nif = self.partner_id.vat or ''
        # Remove common country prefixes (2 letters at start)
        if partner_nif and len(partner_nif) > 2 and partner_nif[:2].isalpha():
            partner_nif = partner_nif[2:]

        # Prepare the complete invoice data according to Verifacti API
        # Using OrderedDict to maintain field order as per API documentation
        invoice_data = OrderedDict([
            ('serie', serie),
            ('numero', numero),
            ('fecha_expedicion', fecha_expedicion),
            ('tipo_factura', 'F1' if self.type == 'out_invoice' else 'R1'),
            ('descripcion', self.comment or self.name or 'Factura'),
            ('nif', partner_nif),
            ('nombre', self.partner_id.name),
            ('lineas', verifacti_lines),
            ('importe_total', str(round(self.amount_total, 2)))
        ])

        return invoice_data
