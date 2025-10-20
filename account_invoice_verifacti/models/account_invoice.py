# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from collections import OrderedDict
import json


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    verifacti_state = fields.Selection([
            ('not_sent', 'Not Sent'),
            ('pending', 'Pending'),
            ('sent', 'Sent'),
            ('error', 'Error')
        ],
        string='Verifacti State',
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

    verifacti_url = fields.Char(
        string='Verifacti URL',
        readonly=True,
        copy=False,
        help='URL to view invoice on Verifacti portal',
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

    verifacti_journal_enabled = fields.Boolean(
        string='Journal has Verifacti enabled',
        related='journal_id.verifacti_enabled',
        readonly=True,
    )

    verifacti_rectification_type = fields.Selection([
            ('S', 'By Substitution'),
            ('I', 'By Differences')
        ],
        string='Rectification Type',
        help='Required for rectificative invoices (R1-R5). Indicates if the rectification is by substitution (S) or by differences (I).',
        required=False,
        copy=False,
    )

    verifacti_operation_date = fields.Date(
        string='Operation Date',
        help='Date of the operation (can be earlier than the invoice date). If not specified, the invoice date is used.',
        copy=False,
    )

    verifacti_incident = fields.Boolean(
        string='Incident',
        readonly=True,
        help='Check if there was any incident in the issuance of this invoice',
        default=False,
        copy=False,
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
        res = super(AccountInvoice, self).action_invoice_open()

        invoices_to_send = self.filtered(
            lambda inv: inv.type in ['out_invoice', 'out_refund'] and
                       inv.company_id.country_id.code == 'ES' and
                       inv.journal_id.verifacti_enabled
        )

        failed_records = []

        for invoice in invoices_to_send:
            if not invoice.company_id.verifacti_active:
                continue

            log_record = None
            try:
                log_record = invoice._create_verifacti_log()
            except Exception as e:
                invoice_identifier = invoice.number or invoice.name or invoice.id
                invoice._reset_after_verifacti_failure()
                failed_records.append((invoice_identifier, str(e)))
                continue

            if log_record and log_record.state in ['error', 'rejected']:
                invoice_identifier = invoice.number or invoice.name or invoice.id
                invoice._reset_after_verifacti_failure()
                error_msg = log_record.error_message or _('Error al enviar a Verifacti')
                failed_records.append((invoice_identifier, error_msg))

        if failed_records:
            self.env.cr.commit()

            error_msg = _(
                'The following invoices could not be sent to Verifacti and have been reverted to draft. '
                'Check the Verifactu log in each invoice for error details:\n\n'
            )
            for inv_name, _message in failed_records:
                error_msg += u'• %s\n' % inv_name
            raise UserError(error_msg)

        return res

    def _create_verifacti_log(self):
        """Create a pending log entry for Verifacti"""
        self.ensure_one()

        if self.verifacti_state in ['sent', 'pending']:
            return False

        invoice_data = self._prepare_verifacti_data()

        log = self.env['verifacti.log'].create({
            'invoice_id': self.id,
            'state': 'pending',
            'request_data': json.dumps(invoice_data, indent=2, ensure_ascii=False)
        })

        self.write({'verifacti_state': 'pending'})

        log.send_to_verifacti()

        return log

    def _reset_after_verifacti_failure(self):
        """Return invoice to draft and flag Verifacti state after a failed send"""
        for invoice in self:
            try:
                if invoice.state not in ['draft', 'cancel']:
                    invoice.action_invoice_cancel()
            except Exception:
                pass

            try:
                if invoice.state != 'draft':
                    invoice.action_invoice_draft()
            except Exception:
                pass

            invoice.write({
                'verifacti_state': 'error',
                'verifacti_id': False,
                'verifacti_qr_code': False,
                'verifacti_url': False
            })

    @api.multi
    def action_check_verifacti_status(self):
        """Manually check the status of this invoice on Verifacti"""
        self.ensure_one()

        log_record = self.verifacti_log_ids.filtered(lambda log: log.verifacti_id).\
            sorted('create_date', reverse=True)[:1]
        if not log_record:
            raise UserError(_('No Verifacti log found with a Verifacti ID for this invoice.'))

        log_record._check_invoice_status()

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def _prepare_verifacti_data(self):
        """
        Prepare invoice data for Verifacti.com API
        Uses the simplified API format, not the full AEAT RegistroAlta structure
        Reference: https://www.verifacti.com/docs
        """
        self.ensure_one()

        invoice_number = self.number or self.name
        if '/' in invoice_number:
            parts = invoice_number.rsplit('/', 1)
            serie = parts[0]
            numero = parts[1]
        else:
            serie = invoice_number[:10]
            numero = invoice_number

        fecha_expedicion = ''
        if self.date_invoice:
            parts = self.date_invoice.split('-')
            if len(parts) == 3:
                fecha_expedicion = '{}-{}-{}'.format(parts[2], parts[1], parts[0])

        if not fecha_expedicion:
            today = fields.Date.today()
            parts = today.split('-')
            fecha_expedicion = '{}-{}-{}'.format(parts[2], parts[1], parts[0])

        partner_nif = self.partner_id.vat or ''
        if partner_nif and len(partner_nif) > 2 and partner_nif[:2].isalpha():
            partner_nif = partner_nif[2:]

        invoice_type = self._get_verifacti_invoice_type()

        invoice_data = OrderedDict()
        invoice_data['serie'] = serie
        invoice_data['numero'] = numero
        invoice_data['fecha_expedicion'] = fecha_expedicion

        operation_date_field = False
        if hasattr(self, 'verifacti_operation_date') and self.verifacti_operation_date:
            operation_date_field = self.verifacti_operation_date
        elif hasattr(self, 'date_operation') and getattr(self, 'date_operation'):
            operation_date_field = getattr(self, 'date_operation')
        if operation_date_field:
            parts = str(operation_date_field).split('-')
            if len(parts) == 3:
                fecha_op = '{}-{}-{}'.format(parts[2], parts[1], parts[0])
                if fecha_op != fecha_expedicion:
                    invoice_data['fecha_operacion'] = fecha_op

        invoice_data['tipo_factura'] = invoice_type

        if invoice_type in ['R1', 'R2', 'R3', 'R4', 'R5']:
            if not self.verifacti_rectification_type:
                raise UserError(_(
                    'The "Rectification Type" field is required for rectificative invoices (R1-R5). '
                    'Select "By Substitution" or "By Differences" in the Verifactu tab.'
                ))
            invoice_data['tipo_rectificativa'] = self.verifacti_rectification_type

        invoice_data['descripcion'] = self._get_invoice_description()

        if invoice_type not in ['F2', 'R5']:
            if partner_nif and self.partner_id.name:
                invoice_data['nif'] = partner_nif
                invoice_data['nombre'] = self.partner_id.name[:120]
            elif self.partner_id.name:
                id_otro = self._get_id_otro()
                if id_otro:
                    invoice_data['id_otro'] = id_otro
                    invoice_data['nombre'] = self.partner_id.name[:120]
                else:
                    raise UserError(_(
                        'For invoice type %s, the recipient\'s NIF or an alternative identifier (passport, etc.) is required.\n'
                        'Configure the VAT in the customer record or use simplified invoices (F2).'
                    ) % invoice_type)

        lineas = []
        if self.tax_line_ids:
            if len(self.tax_line_ids) > 12:
                notify = _(
                    'The invoice has %d tax lines, but Verifacti only allows a maximum of 12 lines.\n'
                    'Group products with the same VAT type into a single line.'
                ) % len(self.tax_line_ids)
                self.message_post(body=notify)

            for tax_line in self.tax_line_ids[:12]:
                tax = tax_line.tax_id

                line_item = OrderedDict()
                line_item['base_imponible'] = '{:.2f}'.format(tax_line.base)

                exempt_operation = self._get_exempt_operation(tax)

                if exempt_operation:
                    line_item['operacion_exenta'] = exempt_operation
                else:
                    line_item['tipo_impositivo'] = '{:.2f}'.format(tax.amount)
                    line_item['cuota_repercutida'] = '{:.2f}'.format(tax_line.amount)

                    surcharge_info = self._get_equivalence_surcharge(tax_line)
                    if surcharge_info:
                        line_item['tipo_recargo_equivalencia'] = '{:.2f}'.format(surcharge_info['tipo'])
                        line_item['cuota_recargo_equivalencia'] = '{:.2f}'.format(surcharge_info['cuota'])

                if hasattr(tax, 'verifacti_tax_type') and tax.verifacti_tax_type and tax.verifacti_tax_type != '01':
                    line_item['impuesto'] = tax.verifacti_tax_type

                if hasattr(tax, 'verifacti_operation_classification') and tax.verifacti_operation_classification:
                    if tax.verifacti_operation_classification != 'S1':
                        line_item['calificacion_operacion'] = tax.verifacti_operation_classification

                regime_code = self._get_regime_code(tax)
                if regime_code and regime_code != '01':
                    line_item['clave_regimen'] = regime_code

                if hasattr(tax, 'verifacti_cost_based_tax_base') and tax.verifacti_cost_based_tax_base:
                    if regime_code in ['06'] or (hasattr(tax, 'verifacti_tax_type') and tax.verifacti_tax_type in ['02', '05']):
                        line_item['base_imponible_a_coste'] = '{:.2f}'.format(tax.verifacti_cost_based_tax_base)

                lineas.append(line_item)
        else:
            line_item = OrderedDict()
            line_item['base_imponible'] = '{:.2f}'.format(self.amount_untaxed)
            line_item['tipo_impositivo'] = '0.00'
            line_item['cuota_repercutida'] = '0.00'

            regime_code = self._get_regime_code(None)
            if regime_code and regime_code != '01':
                line_item['clave_regimen'] = regime_code

            lineas.append(line_item)

        if len(lineas) == 0:
            raise UserError(_('The invoice must have at least one tax line.'))

        if len(lineas) > 12:
            raise UserError(_(
                'The invoice has %d tax lines, but Verifacti only allows a maximum of 12 lines.\n'
                'Group products with the same VAT type into a single line.'
            ) % len(lineas))

        invoice_data['lineas'] = lineas

        if invoice_type in ['R1', 'R2', 'R3', 'R4', 'R5']:
            rectified_invoices = self._get_rectified_invoices()

            if rectified_invoices:
                invoice_data['facturas_rectificadas'] = rectified_invoices

            if self.verifacti_rectification_type == 'S':
                if not rectified_invoices:
                    raise UserError(_(
                        'You must specify the original invoice for substitution rectifications (S). '
                        'Verify that the "Source" field contains the original invoice number.'
                    ))

                rectification_amount = self._get_rectification_amount(rectified_invoices)
                if rectification_amount:
                    invoice_data['importe_rectificativa'] = rectification_amount

        invoice_data['importe_total'] = '{:.2f}'.format(self.amount_total)

        regime_code = self._get_regime_code(None)
        if regime_code not in ['03', '05', '06', '08', '09']:
            total_calculated = sum(
                float(linea.get('base_imponible', 0)) +
                float(linea.get('cuota_repercutida', 0)) +
                float(linea.get('cuota_recargo_equivalencia', 0))
                for linea in lineas
            )
            diferencia = abs(self.amount_total - total_calculated)
            if diferencia > 10.0:
                pass

        if hasattr(self.company_id, 'verifacti_validate_recipient'):
            if not self.company_id.verifacti_validate_recipient:
                invoice_data['validar_destinatario'] = False

        if self.verifacti_incident:
            invoice_data['incidencia'] = 'S'

        return invoice_data

    def _get_verifacti_invoice_type(self):
        """
        Determine invoice type according to Verifacti specification
        """
        self.ensure_one()

        if self.type == 'out_invoice':
            # Regular invoice
            return 'F1'
        elif self.type == 'out_refund':
            return 'R1'
        else:
            return 'F1'

    def _get_invoice_description(self):
        """
        Get a meaningful invoice description for Verifacti
        """
        self.ensure_one()

        description_parts = []

        if self.invoice_line_ids:
            products = []
            for line in self.invoice_line_ids[:5]:
                if line.product_id and line.product_id.name:
                    product_name = line.product_id.name
                    if line.quantity and line.quantity != 1:
                        product_name = '{} x{}'.format(product_name, int(line.quantity))
                    products.append(product_name)
                elif line.name and line.name.strip() and line.name != '/':
                    products.append(line.name.strip())

            if products:
                description_parts.append(', '.join(products))
                remaining = len(self.invoice_line_ids) - 5
                if remaining > 0:
                    description_parts.append('and {} more'.format(remaining))

        if not description_parts:
            if self.comment and self.comment.strip():
                description_parts.append(self.comment.strip())
            elif self.reference and self.reference.strip():
                description_parts.append('Ref: {}'.format(self.reference.strip()))
            elif self.origin and self.origin.strip():
                description_parts.append('Origin: {}'.format(self.origin.strip()))
            elif self.name and self.name != '/':
                description_parts.append(self.name)

        if description_parts:
            description = ' - '.join(description_parts)
        else:
            if self.type == 'out_invoice':
                description = 'Sales Invoice'
            elif self.type == 'out_refund':
                description = 'Rectificative Invoice'
            else:
                description = 'Invoice'

        if len(description) > 500:
            description = description[:497] + '...'

        return description

    def _get_rectified_invoices(self):
        """
        Get the list of original invoices being rectified by this refund

        Returns:
            list: Array of dicts with serie, numero, fecha_expedicion of original invoices
        """
        self.ensure_one()

        rectified_invoices = []

        if self.type == 'out_refund':
            if hasattr(self, 'refund_invoice_id') and self.refund_invoice_id:
                original = self.refund_invoice_id
                rectified_invoices.append(self._format_rectified_invoice(original))

            elif self.origin:
                original_invoices = self.env['account.invoice'].search([
                    ('number', '=', self.origin),
                    ('type', '=', 'out_invoice'),
                    ('partner_id', '=', self.partner_id.id)
                ], limit=1)

                if original_invoices:
                    rectified_invoices.append(self._format_rectified_invoice(original_invoices))

        return rectified_invoices

    def _format_rectified_invoice(self, invoice):
        """
        Format an invoice reference for facturas_rectificadas field
        """
        invoice_number = invoice.number or invoice.name
        if '/' in invoice_number:
            parts = invoice_number.rsplit('/', 1)
            serie = parts[0]
            numero = parts[1]
        else:
            serie = invoice_number[:10]
            numero = invoice_number

        fecha_expedicion = ''
        if invoice.date_invoice:
            parts = invoice.date_invoice.split('-')
            if len(parts) == 3:
                fecha_expedicion = '{}-{}-{}'.format(parts[2], parts[1], parts[0])

        invoice_ref = OrderedDict()
        invoice_ref['serie'] = serie
        invoice_ref['numero'] = numero
        invoice_ref['fecha_expedicion'] = fecha_expedicion

        return invoice_ref

    def _get_rectification_amount(self, invoice_refs):
        """
        Get the importe_rectificativa for rectificative invoices (tipo S - por sustitución)
        """
        self.ensure_one()

        base_rectified_total = 0.0
        surcharge_rectified_total = 0.0
        surcharge_charge_total = 0.0

        if self.type == 'out_refund':
            original_invoice = None

            if hasattr(self, 'refund_invoice_id') and self.refund_invoice_id:
                original_invoice = self.refund_invoice_id
            elif self.origin:
                original_invoices = self.env['account.invoice'].search([
                    ('number', '=', self.origin),
                    ('type', '=', 'out_invoice'),
                    ('partner_id', '=', self.partner_id.id)
                ], limit=1)
                if original_invoices:
                    original_invoice = original_invoices

            if original_invoice:
                base_rectified_total = original_invoice.amount_untaxed
                for tax_line in original_invoice.tax_line_ids:
                    tax = tax_line.tax_id
                    is_surcharge = False
                    if hasattr(tax, 'verifacti_is_surcharge') and tax.verifacti_is_surcharge:
                        is_surcharge = True
                    elif hasattr(tax, 'verifacti_surcharge_rate') and tax.verifacti_surcharge_rate > 0:
                        is_surcharge = True

                    if is_surcharge:
                        surcharge_charge_total += tax_line.amount
                    else:
                        surcharge_rectified_total += tax_line.amount

        rectification_amount = OrderedDict()
        rectification_amount['base_rectificada'] = '{:.2f}'.format(base_rectified_total)
        rectification_amount['cuota_rectificada'] = '{:.2f}'.format(surcharge_rectified_total)

        if surcharge_charge_total > 0:
            rectification_amount['cuota_recargo_rectificada'] = '{:.2f}'.format(surcharge_charge_total)

        return rectification_amount

    def _get_id_otro(self):
        """
        Get alternative identification (id_otro) for foreign partners without Spanish NIF
        """
        self.ensure_one()

        if not self.partner_id.vat:
            return None

        vat = self.partner_id.vat.strip().upper()

        if len(vat) > 2 and vat[:2].isalpha():
            country_code = vat[:2]
            id_value = vat[2:]

            if country_code == 'ES':
                return None

            id_otro = OrderedDict()
            id_otro['id_type'] = '02'
            id_otro['codigo_pais'] = country_code
            id_otro['id'] = id_value[:20]

            return id_otro

        partner_country = self.partner_id.country_id
        if partner_country and partner_country.code != 'ES':
            id_otro = OrderedDict()
            id_otro['id_type'] = '04'
            id_otro['codigo_pais'] = partner_country.code
            id_otro['id'] = vat[:20]

            return id_otro

        return None

    def _get_exempt_operation(self, tax):
        """
        Get operacion_exenta code for exempt operations (E1-E6)
        """
        if not tax:
            return None
        if hasattr(tax, 'verifacti_exempt_operation') and tax.verifacti_exempt_operation:
            return tax.verifacti_exempt_operation
        if tax.amount == 0 and hasattr(tax, 'type_tax_use'):
            pass
        return None

    def _get_equivalence_surcharge(self, tax_line):
        """
        Get recargo de equivalencia (surcharge) info for a tax line
        """

        tax = tax_line.tax_id

        if hasattr(tax, 'verifacti_surcharge_rate') and tax.verifacti_surcharge_rate > 0:
            surcharge_amount = tax_line.base * (tax.verifacti_surcharge_rate / 100.0)
            return {
                'tipo': tax.verifacti_surcharge_rate,
                'cuota': surcharge_amount
            }

        if hasattr(tax, 'children_tax_ids'):
            for child_tax in tax.children_tax_ids:
                if hasattr(child_tax, 'verifacti_is_surcharge') and child_tax.verifacti_is_surcharge:
                    for tl in self.tax_line_ids:
                        if tl.tax_id == child_tax:
                            return {
                                'tipo': child_tax.amount,
                                'cuota': tl.amount
                            }
        return None

    def _get_regime_code(self, tax):
        """
        Get clave_regimen (regime key) for the operation
        """

        if tax and hasattr(tax, 'verifacti_regime_code') and tax.verifacti_regime_code:
            clave = tax.verifacti_regime_code
            if len(clave) > 2:
                clave = clave[:2]
            return clave

        if hasattr(self.company_id, 'verifacti_regime_code') and self.company_id.verifacti_regime_code:
            clave = self.company_id.verifacti_regime_code
            if len(clave) > 2:
                clave = clave[:2]
            return clave

        return '01'
