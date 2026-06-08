# -*- coding: utf-8 -*-
# 2021 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    external_collector_ref = fields.Char(
        readonly=True,
        string="External Collector Ref. (move line)")


class BankPaymentLine(models.Model):
    _inherit = 'bank.payment.line'

    ext_collector_sent = fields.Boolean(
        string="In collection",
        readonly=True,
        help="Indicates whether this payment has already been sent to an "
             "external collector.")

    external_collector_ref = fields.Char(
        readonly=True,
        string="External Collector Ref. (bank line)")


class AccountPaymentOrder(models.Model):
    _inherit = 'account.payment.order'

    @api.multi
    def generate_payment_file(self):
        self.ensure_one()
        pay_method = self.payment_method_id

        if pay_method.code != 'ext_collector':
            return super(AccountPaymentOrder, self).generate_payment_file()

        bank_lines = ""
        for line in self.bank_line_ids:
            bank_line = ""
            if line.ext_collector_sent:
                raise ValidationError(
                    _("The bank line %s has already been sent to external "
                      "collector") % line.name)
            line.external_collector_ref = self.env['ir.sequence'].next_by_code(
                'external_collector_ref_seq')
            line.ext_collector_sent = True

            line_name = line.name
            amount = str(line.amount_currency)
            bank_line = line_name + ' ' + amount + "\n"
            bank_lines += bank_line

        payment_file_str = bank_lines
        filename = 'external_collector_' + \
            datetime.today().strftime("%Y%m%d") + ".txt"

        return payment_file_str, filename

    @api.multi
    def generated2uploaded(self):
        res = super(AccountPaymentOrder, self).generated2uploaded()
        for order in self:
            if order.payment_method_id.code == 'ext_collector':
                for bline in order.bank_line_ids:
                    if bline.ext_collector_sent:
                        for l in bline.payment_line_ids:
                            if bline.name == l.bank_line_id.name:
                                invoice = l.invoice_id
                                invoice.write({
                                    'in_external_collector': True,
                                    'external_collector_ref':
                                        bline.external_collector_ref,
                                    })
                                move_lines = \
                                    self.env['account.move.line'].search([
                                        ('invoice_id', '=', invoice.id)])
                            if move_lines:
                                for move_line in move_lines:
                                    move_line.external_collector_ref = \
                                        bline.external_collector_ref
        return res

    @api.multi
    def action_done_cancel(self):
        for order in self:
            if order.payment_method_id.code == 'ext_collector':
                for bline in order.bank_line_ids:
                    for l in bline.payment_line_ids:
                        if bline.name == l.bank_line_id.name:
                            invoice = l.invoice_id
                            invoice.write({
                                'in_external_collector': False,
                                'external_collector_ref': False,
                                })
        return super(AccountPaymentOrder, self).action_done_cancel()
