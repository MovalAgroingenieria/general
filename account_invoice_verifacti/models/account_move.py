# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json
import logging


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    verifacti_state = fields.Selection([
            ('not_sent', 'Not Sent'),
            ('pending', 'Pending'),
            ('sent', 'Sent'),
            ('error', 'Error')
        ],
        string='Verifacti Status',
        default='not_sent',
        readonly=True,
        copy=False,
    )

    verifacti_id = fields.Char(
        string='Verifacti ID',
        readonly=True,
        copy=False,
    )

    verifacti_qr_code = fields.Binary(
        string='Verifacti QR Code',
        readonly=True,
        copy=False,
    )

    verifacti_log_ids = fields.One2many(
        'verifacti.log',
        'invoice_id',
        string='Verifacti Logs',
        readonly=True,
    )

    verifacti_last_error = fields.Text(
        string='Last Error',
        compute='_compute_verifacti_last_error',
    )

    @api.depends('verifacti_log_ids.error_message')
    def _compute_verifacti_last_error(self):
        for move in self:
            last_log = move.verifacti_log_ids.filtered(
                lambda l: l.state == 'error'
            ).sorted('create_date', reverse=True)[:1]
            move.verifacti_last_error = last_log.error_message if last_log else False

    def action_post(self):
        """Override to send to Verifacti after validation"""
        res = super().action_post()

        invoices_to_send = self.filtered(
            lambda m: m.move_type in ['out_invoice', 'out_refund'] and
                     m.company_id.country_id.code == 'ES'
        )

        for invoice in invoices_to_send:
            config = self.env['verifacti.config'].get_config(invoice.company_id.id)
            if config and config.auto_send:
                invoice._create_verifacti_log()

        return res

    def _create_verifacti_log(self):
        """Create a pending log entry for Verifacti"""
        self.ensure_one()

        if self.verifacti_state in ['sent', 'pending']:
            return

        invoice_data = self._prepare_verifacti_data()

        log = self.env['verifacti.log'].create({
            'invoice_id': self.id,
            'state': 'pending',
            'request_data': json.dumps(invoice_data, indent=2, ensure_ascii=False)
        })

        self.write({'verifacti_state': 'pending'})

        log.send_to_verifacti()

        return log

    def _prepare_verifacti_data(self):
        """Prepare invoice data for Verifacti API"""
        self.ensure_one()

        lines_by_tax = {}
        for line in self.invoice_line_ids.filtered(lambda l: not l.display_type):
            tax_ids = tuple(line.tax_ids.ids) if line.tax_ids else (0,)
            if tax_ids not in lines_by_tax:
                lines_by_tax[tax_ids] = {
                    'lines': [],
                    'taxes': line.tax_ids,
                    'subtotal': 0.0,
                    'tax_amount': 0.0
                }
            lines_by_tax[tax_ids]['lines'].append(line)
            lines_by_tax[tax_ids]['subtotal'] += line.price_subtotal

            taxes_res = line.tax_ids.compute_all(
                line.price_unit,
                quantity=line.quantity,
                currency=line.currency_id,
                product=line.product_id,
                partner=line.partner_id
            )
            lines_by_tax[tax_ids]['tax_amount'] += taxes_res['total_included'] - taxes_res['total_excluded']

        grouped_lines = []
        for tax_group in list(lines_by_tax.values())[:12]:
            tax_rate = 0.0
            if tax_group['taxes']:
                tax_rate = tax_group['taxes'][0].amount if tax_group['taxes'] else 0.0

            line_descriptions = ', '.join(
                line.name or line.product_id.name or 'Product'
                for line in tax_group['lines'][:5]
            )

            grouped_lines.append({
                'description': line_descriptions[:200],
                'quantity': 1,
                'unit_price': tax_group['subtotal'],
                'tax_rate': tax_rate,
                'tax_amount': tax_group['tax_amount'],
                'total': tax_group['subtotal'] + tax_group['tax_amount']
            })

        invoice_data = {
            'invoice_number': self.name,
            'invoice_date': self.invoice_date.isoformat() if self.invoice_date else '',
            'issue_date': fields.Date.today().isoformat(),
            'tax_period': self.invoice_date.strftime('%Y-%m') if self.invoice_date else '',
            'issuer_nif': self.company_id.vat or '',
            'issuer_name': self.company_id.name,
            'issuer_address': self._format_address(self.company_id.partner_id),
            'recipient_nif': self.partner_id.vat or '',
            'recipient_name': self.partner_id.name,
            'recipient_address': self._format_address(self.partner_id),
            'lines': grouped_lines,
            'subtotal': self.amount_untaxed,
            'tax_total': self.amount_tax,
            'total': self.amount_total,
            'invoice_type': 'F1' if self.move_type == 'out_invoice' else 'R1',
            'description': self.narration or '',
        }

        return invoice_data

    def _format_address(self, partner):
        """Format partner address for Verifacti"""
        address_parts = []
        if partner.street:
            address_parts.append(partner.street)
        if partner.street2:
            address_parts.append(partner.street2)
        if partner.city:
            address_parts.append(partner.city)
        if partner.state_id:
            address_parts.append(partner.state_id.name)
        if partner.zip:
            address_parts.append(partner.zip)
        if partner.country_id:
            address_parts.append(partner.country_id.name)

        return ', '.join(address_parts)

    def action_send_verifacti(self):
        """Manual action to send to Verifacti"""
        self.ensure_one()

        if self.state != 'posted':
            raise UserError(_('Only posted invoices can be sent to Verifacti.'))

        if self.move_type not in ['out_invoice', 'out_refund']:
            raise UserError(_('Only customer invoices can be sent to Verifacti.'))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Verifacti'),
                'message': _('Invoice queued for sending to Verifacti.'),
                'type': 'success',
                'sticky': False,
            }
        }
