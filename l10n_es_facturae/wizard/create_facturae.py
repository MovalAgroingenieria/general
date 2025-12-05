# -*- coding: utf-8 -*-
# 2023 Moval Agroingeniería
# © 2009 Alejandro Sanchez <alejandro@asr-oss.com>
# © 2015 Ismael Calvo <ismael.calvo@factorlibre.com>
# © 2015 Tecon
# © 2015 Juanjo Algaz (MalagaTIC)
# © 2015 Omar Castiñeira (Comunitea)
# © 2016 Serv. Tecnol. Avanzados - Pedro M. Baeza
# © 2017 Creu Blanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import base64
import six

from odoo import api, fields, models, _
from odoo.exceptions import Warning as UserError


class Log(Exception):
    def __init__(self):
        self.content = ""
        self.error = False

    def add(self, s, error=True):
        self.content = self.content + s
        if error:
            self.error = error

    def __call__(self):
        return self.content

    def __str__(self):
        return self.content


class CreateFacturae(models.TransientModel):
    _name = "create.facturae"

    facturae = fields.Binary('Factura-E file', readonly=True)
    facturae_fname = fields.Char("File name", size=64)
    note = fields.Text('Log')
    state = fields.Selection([('first', 'First'), ('second', 'Second')],
                             'State', readonly=True, default='first')
    firmar_facturae = fields.Boolean(
        '¿Desea firmar digitalmente el fichero generado?',
        help='Requiere certificado en la ficha de la compañía', default=True)

    def _validate_partner_data(self, invoice):
        """Valida que el partner tenga todos los datos obligatorios"""
        errors = []
        partner = invoice.partner_id
        company = invoice.company_id.partner_id

        # Validar datos del partner (cliente)
        if not partner.name:
            errors.append(_('- Partner name is required'))

        if not partner.vat:
            errors.append(_('- Partner VAT/NIF is required'))
        elif len(partner.vat) < 3:
            errors.append(_('- Partner VAT/NIF is too short (minimum 3 characters)'))

        # Ensure street is a non-empty string (not False, not None, not empty)
        if not partner.street or not isinstance(partner.street, six.string_types) or not partner.street.strip():
            errors.append(_('- Partner street address is required'))

        # Validate street2 is also a string if present (to avoid concatenation issues)
        if partner.street2 and not isinstance(partner.street2, six.string_types):
            errors.append(_('- Partner street2 must be a text value'))

        if not partner.city:
            errors.append(_('- Partner city is required'))

        if not partner.zip:
            errors.append(_('- Partner postal code is required'))

        if not partner.country_id:
            errors.append(_('- Partner country is required'))
        elif not partner.country_id.code_alpha3:
            errors.append(_('- Partner country must have Alpha-3 code configured'))

        if not partner.state_id:
            errors.append(_('- Partner state/province is required'))

        # Validar datos de la compañía
        if not company.name:
            errors.append(_('- Company name is required'))

        if not company.vat:
            errors.append(_('- Company VAT/NIF is required'))
        elif len(company.vat) < 3:
            errors.append(_('- Company VAT/NIF is too short (minimum 3 characters)'))

        # Ensure street is a non-empty string (not False, not None, not empty)
        if not company.street or not isinstance(company.street, six.string_types) or not company.street.strip():
            errors.append(_('- Company street address is required'))

        # Validate street2 is also a string if present (to avoid concatenation issues)
        if company.street2 and not isinstance(company.street2, six.string_types):
            errors.append(_('- Company street2 must be a text value'))

        if not company.city:
            errors.append(_('- Company city is required'))

        if not company.zip:
            errors.append(_('- Company postal code is required'))

        if not company.country_id:
            errors.append(_('- Company country is required'))
        elif not company.country_id.code_alpha3:
            errors.append(_('- Company country must have Alpha-3 code configured'))

        if not company.state_id:
            errors.append(_('- Company state/province is required'))

        # Si hay errores, lanzar excepción con todos los mensajes
        if errors:
            error_msg = _('Cannot generate Factura-E. Missing required data:\n\n') + '\n'.join(errors)
            raise UserError(error_msg)

    @api.multi
    def create_facturae_file(self):
        log = Log()
        invoice_ids = self.env.context.get('active_ids', [])
        if not invoice_ids or len(invoice_ids) > 1:
            raise UserError(_('You can only select one invoice to export'))
        active_model = self.env.context.get('active_model', False)
        assert active_model == 'account.invoice', \
            'Bad context propagation'
        invoice = self.env['account.invoice'].browse(invoice_ids[0])

        self._validate_partner_data(invoice)

        invoice_file, file_name = invoice.ensure_one().get_facturae(
            self.firmar_facturae)

        file = base64.b64encode(invoice_file)
        self.env['ir.attachment'].create({
            'name': file_name,
            'datas': file,
            'datas_fname': file_name,
            'res_model': 'account.invoice',
            'res_id': invoice.id,
            'mimetype': 'application/xml'
        })
        log.add(_("Export successful\n\nSummary:\nInvoice number: %s\n") %
                invoice.number)
        self.write({
            'note': log(),
            'facturae': file,
            'facturae_fname': file_name,
            'state': 'second'
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'create.facturae',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
