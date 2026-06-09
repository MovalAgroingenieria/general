# -*- coding: utf-8 -*-
# 2021 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from jinja2 import Template, TemplateError
from datetime import datetime
import random
import re
from odoo import models, fields, api, exceptions, _


class NRSTemplate(models.Model):
    _name = 'nrs.template'
    _description = "SMS template"

    name = fields.Char(
        string="Name",
        required=True)

    type = fields.Selection([
        ('partner', 'Partner'),
        ('invoice', 'Invoice')],
        string="Type",
        default="partner",
        required=True,
        help="Type of template")

    subject = fields.Char(
        string="Subject",
        size=100,
        help="Subject of SMS. Limit to 100 characters")

    template = fields.Text(
        string="Template",
        help="Template with jinja2 variables")

    template_resolved = fields.Text(
        string="Template resolved",
        readonly=True,
        help="The template after resolve variables using random item.")

    template_from_wizard = fields.Boolean(
        default=False,
        compute="_compute_template_from_wizard")

    number_of_characters = fields.Integer(
        string="Number of Characters",
        readonly=True,
    )

    sms_encoding = fields.Selection([
        ('gsm', 'GSM 7'),
        ('utf-16', 'UTF 16')],
        string="SMS encoding",
        readonly=True,
    )

    number_of_sms = fields.Integer(
        string="Number of SMS",
        readonly=True,
    )

    _sql_constraints = [
        ('unique_wausms_template', 'UNIQUE (name, type)', 'Existing template.')
        ]

    def _escape_json_special_chars(self, string):
        escaped_string = string.replace('\n', '\\n').replace(
            '"', '\\"').replace('\b', '\\b').replace(
            '\t', '\\t').replace('\f', '\\f').replace('\r', '\\r')
        return escaped_string

    def _extract_encoding(self, content):
        if not isinstance(content, unicode):
            content = content.decode('utf-8')

        encoding = 'utf-16'
        gsm7_pattern = re.compile(
            ur"^[@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ "
            ur"!\"#¤%&'()*+,-./0123456789:;<=>?¡"
            ur"ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿"
            ur"abcdefghijklmnopqrstuvwxyzäöñüà]*$")

        if gsm7_pattern.match(content):
            encoding = 'gsm'
        return encoding

    def _calculate_number_of_sms(self, num_char, encoding):
        if num_char == 0:
            return 0
        if encoding == 'utf-16':
            if num_char <= 70:
                return 1
            return -(-num_char // 67)
        if num_char <= 160:
            return 1
        return -(-num_char // 153)

    def _get_random_invoice(self):
        invoice = ""
        invoice_ids = self.env['account.invoice'].search([], limit=1000).ids
        if len(invoice_ids) > 0:
            random_invoice_id = random.choice(invoice_ids)
            invoice = self.env['account.invoice'].browse(random_invoice_id)
        else:
            raise exceptions.ValidationError(_("No invoice found"))
        return invoice

    def _get_random_partner(self):
        partner = ""
        partner_ids = self.env['res.partner'].search([], limit=1000).ids
        if len(partner_ids) > 0:
            random_partner_id = random.choice(partner_ids)
            partner = self.env['res.partner'].browse(random_partner_id)
        else:
            raise exceptions.ValidationError(_("No partner found"))
        return partner

    def _get_template_render_context_partner(self):
        partner = self._get_random_partner()
        render_context = {"partner": partner, "datetime": datetime}
        return render_context

    def _get_template_render_context_invoice(self):
        invoice = self._get_random_invoice()
        partner = invoice.partner_id
        render_context = {
            "partner": partner, "invoice": invoice, "datetime": datetime}
        return render_context

    def _get_template_render_context(self):
        builder = getattr(
            self, "_get_template_render_context_%s" % self.type, None)
        if not builder:
            raise exceptions.ValidationError(
                _("Unknown template type: %s") % self.type)
        return builder()

    @api.multi
    def action_resolve_template(self):
        self.ensure_one()
        message = ""
        if self.template:
            try:
                raw_message = Template(self.template).render(
                    **self._get_template_render_context())
            except TemplateError as err:
                raise exceptions.ValidationError(
                    _("Error resolving template: {}".format(err.message)))
            message = self._escape_json_special_chars(raw_message)
        # Number of sms
        encoding = self._extract_encoding(message)
        self.sms_encoding = encoding
        num_char = len(message)
        self.number_of_characters = num_char
        number_of_sms = self._calculate_number_of_sms(num_char, encoding)
        self.number_of_sms = number_of_sms
        # Check size
        if len(message) > 1530:
            raise exceptions.ValidationError(
                _("Number of characters must not exceed 1530"))
        if message:
            self.template_resolved = message

    @api.multi
    def _compute_template_from_wizard(self):
        self.ensure_one()
        context = self._context
        if context.get("from_wizard"):
            self.template_from_wizard = True
