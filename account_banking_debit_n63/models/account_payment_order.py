# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, _
import logging
from datetime import datetime
import re


class BankPaymentLine(models.Model):
    _inherit = 'bank.payment.line'

    n63_s1_ref = fields.Char(
        string="N63 Stage 1 Reference",
        readonly=True,
        help='This number indicates the payment reference if it has '
             'been made by n63 in Stage 1')

    n63_s3_ref = fields.Char(
        string="N63 Stage 3 Reference",
        readonly=True,
        help='This number indicates the payment reference if it has '
             'been made by N63 in Stage 3')

    n63_s1_sent = fields.Boolean(
        string="N63 Stage 1 done",
        readonly=True,
        help='Indicates whether this payment has already been added '
             'to an N63 stage 1')

    n63_s3_sent = fields.Boolean(
        string="N63 Stage 3 done",
        readonly=True,
        help='Indicates whether this payment has already been added '
             'to an N63 stage 3')


class AccountPaymentOrder(models.Model):
    _inherit = 'account.payment.order'

    ENCODING_NAME = 'ascii'
    ENCODING_TYPE = 'replace'
    REGISTR_CODE_HEADER = '4'
    REGISTR_CODE_FOOTER = '8'
    REGISTR_CODE_LINE = '6'

    # Error mode
    error_mode = fields.Selection([
        ('strict', 'Strict'),
        ('permissive', 'Permissive')],
        string="Error mode",
        default="strict",
        help="Strict mode does not allow errors. The permissive mode allows "
             "but they are collected in the 'Errors' tab.' This applies to "
             "both payment file and direct debit file")

    # Errors tab
    errors_found = fields.Text('Errors', readonly=True)

    # Fields
    payment_mode_name = fields.Char(
        compute='_compute_payment_mode_name',
        string="Payment mode name")

    # New n63 fields for phase 1 & 3
    nrbe_entity_code = fields.Char(
        string="NRBE Entity Code",
        help="Code of the entity that sends the delegated charge to N63")

    phase = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
        ('6', '6')],
        string="Phase",
        compute='_compute_phase',
        store=True,
        help="Phase in which the charge is made")

    date_of_obtaining_the_file = fields.Date(
        string="Date of obtaining the file",
        default=fields.Date.today,
        help="Date on which the file is obtained")

    ine_code_issuring_organisation = fields.Char(
        string="INE Code Issuring Organisation",
        help="INE code of the organisation that issues the file")

    # Methods
    @api.depends('payment_mode_id')
    def _compute_payment_mode_name(self):
        # @INFO: payment mode name SUMA (mandatory)
        for record in self:
            record.payment_mode_name = record.payment_mode_id.name

    # On change payment mode force date_prefered
    @api.onchange('payment_mode_name')
    def _onchange_payment_mode_name(self):
        if self.payment_mode_name in ('N63 Fase 1', 'N63 Fase 3'):
            self.date_prefered = 'now'

    @api.depends('payment_mode_id')
    def _compute_phase(self):
        for record in self:
            if record.payment_mode_id.name == 'N63 Fase 1':
                record.phase = '1'
            elif record.payment_mode_id.name == 'N63 Fase 2':
                record.phase = '2'
            elif record.payment_mode_id.name == 'N63 Fase 3':
                record.phase = '3'
            elif record.payment_mode_id.name == 'N63 Fase 4':
                record.phase = '4'
            elif record.payment_mode_id.name == 'N63 Fase 5':
                record.phase = '5'
            elif record.payment_mode_id.name == 'N63 Fase 6':
                record.phase = '6'

    # Generate payment file
    @api.multi
    def generate_payment_file(self):
        self.ensure_one()
        _log = logging.getLogger(self.__class__.__name__)
        pay_method = self.payment_method_id

        if pay_method.code not in ('debit_n63_s1', 'debit_n63_s3'):
            return super(AccountPaymentOrder, self).generate_payment_file()
        header_line = ""
        bank_lines = ""
        footer_line = ""
        total_amount_to_be_attached = 0
        # Generate header
        # Position A [01-01] Length 01 Format N
        header_registre_code = self.REGISTR_CODE_HEADER
        header_line += header_registre_code
        # Position B [02-03] Length 02 Format N
        # free
        pos_b = str(' ' * 2)
        header_line += pos_b

        # Position C [04-07] Length 04 Format N
        nrbe_entity_code = self.nrbe_entity_code
        if nrbe_entity_code:
            header_line += nrbe_entity_code
        else:
            header_line += str(' ' * 4)
        # Position D [08-15] Length 08 Format N
        # free
        pos_d = str(' ' * 8)
        header_line += pos_d

        # Position E [16-23] Length 08 Format N
        # free
        pos_e = str(' ' * 8)
        header_line += pos_e

        # Position F [24-56] Length 33 Format A
        # Position F1 [24-24] Length 01 Format N
        phase = self.phase
        header_line += phase

        # Position F2 [25-32] Length 08 Format N
        date_of_obtaining_the_file = self.date_of_obtaining_the_file
        header_line += date_of_obtaining_the_file.replace('-', '')

        # Position F3 [33-40] Length 08 Format N
        # Only for phases 2, 4, and 6
        pos_f3 = str('0' * 8)
        header_line += pos_f3

        # Position F4 [41-54] Length 14 Format N
        # free
        pos_f4 = str(' ' * 14)
        header_line += pos_f4

        # Position F5 [55-56] Length 02 Format N
        # free
        pos_f5 = str(' ' * 2)
        header_line += pos_f5

        # Position G [57-111] Length 55 Format A
        # Position G1 [57-65] Length 09 Format N
        nif_issuing_organisation = self.env['ir.values'].get_default(
            'account.config.settings', 'nif_issuing_organisation')
        if not nif_issuing_organisation:
            nif_issuing_organisation = str(' ' * 9)
        header_line += nif_issuing_organisation

        # Position G2 [66-71] Length 06 Format N
        ine_code_issuring_organisation = self.ine_code_issuring_organisation
        if ine_code_issuring_organisation:
            if len(ine_code_issuring_organisation) > 6:
                ine_code_issuring_organisation = (
                    ine_code_issuring_organisation)[:6]
            else:
                ine_code_issuring_organisation = (
                    str('0' * (6 - len(ine_code_issuring_organisation))) +
                    ine_code_issuring_organisation)
            header_line += ine_code_issuring_organisation[:6]
        else:
            header_line += str('0' * 6)

        # Position G3 [72-111] Length 40 Format A
        issuring_name = self.env['ir.values'].get_default(
            'account.config.settings', 'issuring_name')
        if issuring_name:
            if len(issuring_name) > 40:
                issuring_name = issuring_name[:40]
            else:
                issuring_name += str(' ' * (40 - len(issuring_name)))
        else:
            issuring_name = str(' ' * 40)
        header_line += issuring_name[:40]

        # Position H [112-650] Length 539 Format A
        # Position H1 [112-116] Length 05 Format N
        notebook_version = '63033'
        header_line += notebook_version

        # Position H2 [117-650] Length 534 Format A
        # free
        pos_h2 = str(' ' * 534)
        header_line += pos_h2
        _log.info('BANK LINE FIELD Total Line         (length %s [651]): %s'
                  % (str(len(header_line)).zfill(3), header_line))
        qty_registers = 2

        # # Generate Lines datas
        for payment in self.bank_line_ids:
            bank_line = ""
            # # Position A [01-01] Length 01 Format N
            header_registre_code = self.REGISTR_CODE_LINE
            pos_a = header_registre_code

            # Position B [02-106] Length 105 Format A
            # Position B1 [2-10] Length 09 Format N
            nif_customer = payment.partner_id.vat[-9:] \
                if payment.partner_id.vat else None
            if nif_customer:
                pos_b1 = nif_customer
            else:
                pos_b1 = str(' ' * 9)

            # Position B2 [11-50] Length 40 Format A
            if payment.partner_id.company_type == 'person':
                customer_name = (payment.partner_id.lastname + ' *' +
                                 payment.partner_id.lastname2 + ' *' +
                                 payment.partner_id.firstname)
            else:
                customer_name = (payment.partner_id.name)
            if customer_name:
                if len(customer_name) > 40:
                    customer_name = customer_name[:40]
                else:
                    customer_name += str(' ' * (40 - len(customer_name)))
            pos_b2 = customer_name[:40]

            # # Position B3 [51-89] Length 39 Format A
            if payment.partner_id.street_num:
                customer_address = payment.partner_id.street + ', ' + (
                    payment.partner_id.street_num)
            else:
                customer_address = payment.partner_id.street
            if customer_address:
                if len(customer_address) > 39:
                    customer_address = customer_address[:39]
                else:
                    customer_address += str(' ' * (39 - len(customer_address)))
            else:
                customer_address = str(' ' * 39)
            pos_b3 = customer_address[:39]

            # # Position B4 [90-101] Length 12 Format N
            town = payment.partner_id.city
            if town:
                if len(town) > 12:
                    town = town[:12]
                else:
                    town += str(' ' * (12 - len(town)))
            else:
                town = str(' ' * 12)
            pos_b4 = town[:12]

            # Position B5 [102-106] Length 05 Format N
            postal_code = payment.partner_id.zip
            if not postal_code:
                postal_code = str(' ' * 5)
            pos_b5 = postal_code

            # Position C [107-119] Length 13 Format N
            debit_identifier = re.sub(r'\D', '', payment.name or '')
            if debit_identifier:
                if len(debit_identifier) > 13:
                    debit_identifier = debit_identifier[:13]
                else:
                    debit_identifier = str('0' * (13 - len(
                        debit_identifier)) + debit_identifier)
            pos_c = debit_identifier

            if phase == "1":
                # Stage 1:
                # Position D [120-134] Length 15 Format N
                # free
                pos_d_p1 = str(' ' * 15)

                # Position E [135-142] Length 08 Format N
                optional_debit_identifier = re.sub(
                    r'\D', '', payment.partner_id.vat or '')
                if optional_debit_identifier:
                    pos_e_p1 = optional_debit_identifier[:8]
                else:
                    pos_e_p1 = str(' ' * 8)

                # Position F [143-157] Length 15 Format N
                # free
                pos_f_p1 = str(' ' * 15)

                # Position G [158-158] Length 01 Format N
                # free
                pos_g_p1 = str(' ' * 1)

                # Position H [159-166] Length 08 Format N
                # free
                pos_h_p1 = str(' ' * 8)

                # Position I [167-174] Length 08 Format N
                # free
                pos_i_p1 = str(' ' * 8)

                # Position J [175-285] Length 111 Format A
                # free
                pos_j_p1 = str(' ' * 111)

                # Position K [286-291] Length 06 Format N
                # free
                pos_k_p1 = str(' ' * 6)

                # Position L [292-327] Length 36 Format A
                # free
                pos_l_p1 = str(' ' * 36)

                # Position M [328-650] Length 323 Format A
                # free
                pos_m_p1 = str(' ' * 323)
                bank_line = (pos_a + pos_b1 + pos_b2 + pos_b3 + pos_b4 +
                             pos_b5 + pos_c + pos_d_p1 + pos_e_p1 + pos_f_p1 +
                             pos_g_p1 + pos_h_p1 + pos_i_p1 + pos_j_p1 +
                             pos_k_p1 + pos_l_p1 + pos_m_p1 + '\r\n')
            if phase == "3":
                # Stage 3:
                # Position D [120-134] Length 15 Format N
                total_amount_attached = payment.amount_currency
                formatted_total_amount_attached = (
                    "{:.2f}".format(total_amount_attached))
                total_amount_attached_without_separator = (
                    formatted_total_amount_attached.replace(
                        '.', ''))
                total_amount_to_be_attached += total_amount_attached
                if total_amount_attached:
                    pos_d_p3 = str(
                        '0' * (15 - len(str(
                            total_amount_attached_without_separator))) +
                        total_amount_attached_without_separator)
                else:
                    pos_d_p3 = str('0' * 15)

                # Position E [135-142] Length 08 Format N
                optional_debit_identifier = re.sub(
                    r'\D', '', payment.partner_id.vat or '')
                if optional_debit_identifier:
                    pos_e_p3 = optional_debit_identifier[:8]
                else:
                    pos_e_p3 = str(' ' * 8)

                # Position F [143-157] Length 15 Format N
                # free
                pos_f_p3 = str(' ' * 15)

                # Position G [158-158] Length 01 Format N
                # free
                pos_g_p3 = str(' ' * 1)

                # Position H [159-166] Length 08 Format N
                # free
                pos_h_p3 = str(' ' * 8)

                # Position I [167-174] Length 08 Format N
                # free
                pos_i_p3 = str(' ' * 8)

                # Position J [175-420] Length 246 Format A

                # Position J1 [175-198] Length 24 Format A
                bank_ids = payment.partner_id.bank_ids
                if bank_ids:
                    if bank_ids[0] and bank_ids[0].acc_number:
                        account_bank_1 = bank_ids[0].acc_number.replace(
                            ' ', '')
                        if len(account_bank_1) > 24:
                            pos_j1_p3 = account_bank_1[:24]
                        else:
                            pos_j1_p3 = account_bank_1 + str(' ' * (24 - len(
                                account_bank_1)))
                    else:
                        pos_j1_p3 = str(' ' * 24)

                    # Position J2 [199-200] Length 02 Format N
                    # free
                    pos_j2_p3 = str(' ' * 2)

                    # Position J3 [201-215] Length 15 Format N
                    # free
                    pos_j3_p3 = str(' ' * 15)

                    # Position J4 [216-239] Length 24 Format A
                    if len(bank_ids) > 1:
                        if bank_ids[1].acc_number:
                            account_bank_2 = bank_ids[1].acc_number.replace(
                                ' ', '')
                            if len(account_bank_2) > 24:
                                pos_j4_p3 = account_bank_2[:24]
                            else:
                                pos_j4_p3 = account_bank_2 + str(' ' * (
                                    24 - len(account_bank_2)))
                        else:
                            pos_j4_p3 = str(' ' * 24)
                    else:
                        pos_j4_p3 = str(' ' * 24)

                    # Position J5 [240-241] Length 02 Format N
                    # free
                    pos_j5_p3 = str(' ' * 2)

                    # Position J6 [242-256] Length 15 Format N
                    # free
                    pos_j6_p3 = str(' ' * 15)

                    # Position J7 [257-280] Length 24 Format A
                    if len(bank_ids) > 2:
                        if bank_ids[2].acc_number:
                            account_bank_3 = bank_ids[2].acc_number.replace(
                                ' ', '')
                            if len(account_bank_3) > 24:
                                pos_j7_p3 = account_bank_3[:24]
                            else:
                                pos_j7_p3 = account_bank_3 + str(' ' * (
                                    24 - len(account_bank_3)))
                        else:
                            pos_j7_p3 = str(' ' * 24)
                    else:
                        pos_j7_p3 = str(' ' * 24)

                    # Position J8 [281-282] Length 02 Format N
                    # free
                    pos_j8_p3 = str(' ' * 2)

                    # Position J9 [283-297] Length 15 Format N
                    # free
                    pos_j9_p3 = str(' ' * 15)

                    # Position J10 [298-321] Length 24 Format A
                    if len(bank_ids) > 3:
                        if bank_ids[3].acc_number:
                            account_bank_4 = bank_ids[3].acc_number.replace(
                                ' ', '')
                            if len(account_bank_4) > 24:
                                pos_j10_p3 = account_bank_4[:24]
                            else:
                                pos_j10_p3 = account_bank_4 + str(' ' * (
                                    24 - len(account_bank_4)))
                        else:
                            pos_j10_p3 = str(' ' * 24)
                    else:
                        pos_j10_p3 = str(' ' * 24)

                    # Position J11 [322-323] Length 02 Format N
                    # free
                    pos_j11_p3 = str(' ' * 2)

                    # Position J12 [324-338] Length 15 Format N
                    # free
                    pos_j12_p3 = str(' ' * 15)

                    # Position J13 [339-362] Length 24 Format A
                    if len(bank_ids) > 4:
                        if bank_ids[4].acc_number:
                            account_bank_5 = bank_ids[4].acc_number.replace(
                                ' ', '')
                            if len(account_bank_5) > 24:
                                pos_j13_p3 = account_bank_5[:24]
                            else:
                                pos_j13_p3 = account_bank_5 + str(' ' * (
                                    24 - len(account_bank_5)))
                        else:
                            pos_j13_p3 = str(' ' * 24)
                    else:
                        pos_j13_p3 = str(' ' * 24)

                    # Position J14 [363-364] Length 02 Format N
                    # free
                    pos_j14_p3 = str(' ' * 2)

                    # Position J15 [365-379] Length 15 Format N
                    # free
                    pos_j15_p3 = str(' ' * 15)

                    # Position J16 [380-403] Length 24 Format A
                    if len(bank_ids) > 5:
                        if bank_ids[5].acc_number:
                            account_bank_6 = bank_ids[5].acc_number.replace(
                                ' ', '')
                            if len(account_bank_6) > 24:
                                pos_j16_p3 = account_bank_6[:24]
                            else:
                                pos_j16_p3 = account_bank_6 + str(' ' * (
                                    24 - len(account_bank_6)))
                        else:
                            pos_j16_p3 = str(' ' * 24)
                    else:
                        pos_j16_p3 = str(' ' * 24)

                    # Position J17 [404-405] Length 02 Format N
                    # free
                    pos_j17_p3 = str(' ' * 2)

                    # Position J18 [406-420] Length 15 Format N
                    # free
                    pos_j18_p3 = str(' ' * 15)
                    pos_j_p3 = (pos_j1_p3 + pos_j2_p3 + pos_j3_p3 + pos_j4_p3 +
                                pos_j5_p3 + pos_j6_p3 + pos_j7_p3 + pos_j8_p3 +
                                pos_j9_p3 + pos_j10_p3 + pos_j11_p3 +
                                pos_j12_p3 + pos_j13_p3 + pos_j14_p3 +
                                pos_j15_p3 + pos_j16_p3 + pos_j17_p3 +
                                pos_j18_p3)
                else:
                    pos_j_p3 = str(' ' * 246)

                # Position K [421-426] Length 06 Format N
                # free
                pos_k_p3 = str(' ' * 6)

                # Position L [427-498] Length 72 Format A
                pos_l_p3 = str(' ' * 72)

                # Position M [499-650] Length 152 Format A
                # free
                pos_m_p3 = str(' ' * 152)
                bank_line = (pos_a + pos_b1 + pos_b2 + pos_b3 + pos_b4 +
                             pos_b5 + pos_c + pos_d_p3 + pos_e_p3 + pos_f_p3 +
                             pos_g_p3 + pos_h_p3 + pos_i_p3 + pos_j_p3 +
                             pos_k_p3 + pos_l_p3 + pos_m_p3 + '\r\n')

            qty_registers += 1
            # Log the payment file
            # Log bank line fields with length [and expected length]
            _log.info('NEW BANK LINE. Number %s #########################'
                      % str(nif_customer).zfill(5))
            _log.info('BANK LINE FIELD Registre Code     (length %s [001]): %s'
                      % (str(len(pos_a)).zfill(3), pos_a))
            _log.info('BANK LINE FIELD NIF               (length %s [009]): %s'
                      % (str(len(pos_b1)).zfill(3), pos_b1))
            _log.info('BANK LINE FIELD Customer Name     (length %s [040]): %s'
                      % (str(len(pos_b2)).zfill(3), pos_b2))
            _log.info('BANK LINE FIELD Customer Address  (length %s [039]): %s'
                      % (str(len(pos_b3)).zfill(3), pos_b3))
            _log.info('BANK LINE FIELD Town              (length %s [012]): %s'
                      % (str(len(pos_b4)).zfill(3), pos_b4))
            _log.info('BANK LINE FIELD Postal Code       (length %s [005]): %s'
                      % (str(len(pos_b5)).zfill(3), pos_b5))
            _log.info('BANK LINE FIELD Debit Identifier  (length %s [013]): %s'
                      % (str(len(pos_c)).zfill(3), pos_c))
            if phase == "1":
                _log.info('BANK LINE FIELD Free Pos D        (length %s [015])'
                          ': %s' % (str(len(pos_d_p1)).zfill(3), pos_d_p1))
                _log.info('BANK LINE FIELD Opt Debit Id      (length %s [008])'
                          ': %s' % (str(len(pos_e_p1)).zfill(3), pos_e_p1))
                _log.info('BANK LINE FIELD Free Pos F        (length %s [015])'
                          ': %s' % (str(len(pos_f_p1)).zfill(3), pos_f_p1))
                _log.info('BANK LINE FIELD Free Pos G        (length %s [001])'
                          ': %s' % (str(len(pos_g_p1)).zfill(3), pos_g_p1))
                _log.info('BANK LINE FIELD Free Pos H        (length %s [008])'
                          ': %s' % (str(len(pos_h_p1)).zfill(3), pos_h_p1))
                _log.info('BANK LINE FIELD Free Pos I        (length %s [008])'
                          ': %s' % (str(len(pos_i_p1)).zfill(3), pos_i_p1))
                _log.info('BANK LINE FIELD Free Pos J        (length %s [111])'
                          ': %s' % (str(len(pos_j_p1)).zfill(3), pos_j_p1))
                _log.info('BANK LINE FIELD Free Pos K        (length %s [006])'
                          ': %s' % (str(len(pos_k_p1)).zfill(3), pos_k_p1))
                _log.info('BANK LINE FIELD Free Pos L        (length %s [036])'
                          ': %s' % (str(len(pos_l_p1)).zfill(3), pos_l_p1))
                _log.info('BANK LINE FIELD Free Pos M        (length %s [323])'
                          ': %s' % (str(len(pos_m_p1)).zfill(3), pos_m_p1))
            if phase == "3":
                _log.info('BANK LINE FIELD Tot amount att   (length %s [015]):'
                          ' %s' % (str(len(pos_d_p3)).zfill(3), pos_d_p3))
                _log.info('BANK LINE FIELD Opt Debit Id     (length %s [008]):'
                          ' %s' % (str(len(pos_e_p3)).zfill(3), pos_e_p3))
                _log.info('BANK LINE FIELD Free Pos F       (length %s [015]):'
                          ' %s' % (str(len(pos_f_p3)).zfill(3), pos_f_p3))
                _log.info('BANK LINE FIELD Free Pos G       (length %s [001]):'
                          ' %s' % (str(len(pos_g_p3)).zfill(3), pos_g_p3))
                _log.info('BANK LINE FIELD Free Pos H       (length %s [008]):'
                          ' %s' % (str(len(pos_h_p3)).zfill(3), pos_h_p3))
                _log.info('BANK LINE FIELD Free Pos I       (length %s [008]):'
                          ' %s' % (str(len(pos_i_p3)).zfill(3), pos_i_p3))
                if bank_ids:
                    _log.info('BANK LINE FIELD Acc Bank 1    (length %s [024])'
                              ': %s' % (str(len(pos_j1_p3)).zfill(3),
                                        pos_j1_p3))
                    _log.info('BANK LINE FIELD Free J2      length %s [002]):'
                              ' %s' % (str(len(pos_j2_p3)).zfill(3), pos_j2_p3)
                              )
                    _log.info('BANK LINE FIELD Free J3       length %s [015]):'
                              ' %s' % (str(len(pos_j3_p3)).zfill(3), pos_j3_p3)
                              )
                    _log.info('BANK LINE FIELD Acc Bank 2    (length %s [024])'
                              ': %s' % (str(len(pos_j4_p3)).zfill(3),
                                        pos_j4_p3))
                    _log.info('BANK LINE FIELD Free J5       (length %s [002])'
                              ': %s' % (str(len(pos_j5_p3)).zfill(3),
                                        pos_j5_p3))
                    _log.info('BANK LINE FIELD Free J6       (length %s [015])'
                              ': %s' % (str(len(pos_j6_p3)).zfill(3),
                                        pos_j6_p3))
                    _log.info('BANK LINE FIELD Acc Bank 3    (length %s [024])'
                              ': %s' % (str(len(pos_j7_p3)).zfill(3),
                                        pos_j7_p3))
                    _log.info('BANK LINE FIELD Free J8       (length %s [002])'
                              ': %s' % (str(len(pos_j8_p3)).zfill(3),
                                        pos_j8_p3))
                    _log.info('BANK LINE FIELD Free J9       (length %s [015])'
                              ': %s' % (str(len(pos_j9_p3)).zfill(3),
                                        pos_j9_p3))
                    _log.info('BANK LINE FIELD Acc Bank 4    (length %s [024])'
                              ': %s' % (str(len(pos_j10_p3)).zfill(3),
                                        pos_j10_p3))
                    _log.info('BANK LINE FIELD Free J11      (length %s [002])'
                              ': %s' % (str(len(pos_j11_p3)).zfill(3),
                                        pos_j11_p3))
                    _log.info('BANK LINE FIELD Free J12      (length %s [015])'
                              ': %s' % (str(len(pos_j12_p3)).zfill(3),
                                        pos_j12_p3))
                    _log.info('BANK LINE FIELD Acc Bank 5    (length %s [024])'
                              ': %s' % (str(len(pos_j13_p3)).zfill(3),
                                        pos_j13_p3))
                    _log.info('BANK LINE FIELD Free J14      (length %s [002])'
                              ': %s' % (str(len(pos_j14_p3)).zfill(3),
                                        pos_j14_p3))
                    _log.info('BANK LINE FIELD Free J15      (length %s [015])'
                              ': %s' % (str(len(pos_j15_p3)).zfill(3),
                                        pos_j15_p3))
                    _log.info('BANK LINE FIELD Acc Bank 6    (length %s [024])'
                              ': %s' % (str(len(pos_j16_p3)).zfill(3),
                                        pos_j16_p3))
                    _log.info('BANK LINE FIELD Free J17      (length %s [002])'
                              ': %s' % (str(len(pos_j17_p3)).zfill(3),
                                        pos_j17_p3))
                    _log.info('BANK LINE FIELD Free J18      (length %s [015])'
                              ': %s' % (str(len(pos_j18_p3)).zfill(3),
                                        pos_j18_p3))
                    _log.info('BANK LINE FIELD Free Pos K    (length %s [006])'
                              ': %s' % (str(len(pos_k_p3)).zfill(3), pos_k_p3))
                else:
                    _log.info('BANK LINE FIELD Free Pos J       (length %s [24'
                              '6]): %s' % (str(len(pos_j_p3)).zfill(3),
                                           pos_j_p3))
                _log.info('BANK LINE FIELD Free Pos L       (length %s [072]):'
                          ' %s' % (str(len(pos_l_p3)).zfill(3), pos_l_p3))

                _log.info('BANK LINE FIELD Free Pos M       (length %s [152]):'
                          ' %s' % (str(len(pos_m_p3)).zfill(3), pos_m_p3))
            _log.info('BANK LINE FIELD Total Line        (length %s [651]): %s'
                      % (str(len(bank_line)).zfill(3), bank_line))
            bank_lines += bank_line
        # Generate footer
        # Position A [01-01] Length 01 Format N
        footer_registre_code = self.REGISTR_CODE_FOOTER
        footer_line += footer_registre_code
        # Position B [02-03] Length 02 Format N
        # free
        footer_line += str(' ' * 2)

        # Position C [04-07] Length 04 Format N
        nrbe_entity_code = self.nrbe_entity_code
        footer_line += nrbe_entity_code

        # Position D [08-15] Length 08 Format N
        number_of_records_in_the_file = qty_registers
        number_8_digits = str(number_of_records_in_the_file).zfill(8)
        footer_line += number_8_digits

        # Position E [16-23] Length 08 Format N
        # free
        pos_e = str(' ' * 8)
        footer_line += pos_e

        # Position F [24-53] Length 30 Format A

        # Position F1 [24-38] Length 15 Format N
        total_amount_to_be_attached = (
            "{:.2f}".format(total_amount_to_be_attached))
        total_amount_to_be_attached_wo = total_amount_to_be_attached.replace(
            '.', '')
        footer_line += str(total_amount_to_be_attached_wo).zfill(15)

        # Position F2 [39-53] Length 15 Format N (only for phase 4, rest 0)
        if self.phase == 4:
            total_amount_retained = self.total_amount_retained
            footer_line += str(total_amount_retained).zfill(15)
        else:
            footer_line += str('0' * 15)

        # Position G [54-62] Length 9 Format N

        # Position G1 [54-62] Length 09 Format N
        nif_issuing_organisation = self.env['ir.values'].get_default(
            'account.config.settings', 'nif_issuing_organisation')
        if not nif_issuing_organisation:
            nif_issuing_organisation = str(' ' * 9)
        footer_line += nif_issuing_organisation

        # Position G2 [63-68] Length 06 Format N
        ine_code_issuring_organisation = self.ine_code_issuring_organisation
        if ine_code_issuring_organisation:
            if len(ine_code_issuring_organisation) > 6:
                ine_code_issuring_organisation = (
                    ine_code_issuring_organisation)[:6]
            else:
                ine_code_issuring_organisation = (
                    str('0' * (6 - len(ine_code_issuring_organisation))) +
                    ine_code_issuring_organisation)
            footer_line += ine_code_issuring_organisation
        else:
            footer_line += str('0' * 6)

        # Position G3 [69-108] Length 40 Format A
        issuring_name = self.env['ir.values'].get_default(
            'account.config.settings', 'issuring_name')
        if issuring_name:
            if len(issuring_name) > 40:
                issuring_name = issuring_name[:40]
            else:
                issuring_name += str(' ' * (40 - len(issuring_name)))
        else:
            issuring_name = str(' ' * 40)
        footer_line += issuring_name[:40]

        # Position H [109-651] Length 542 Format A
        # free
        pos_h2 = str(' ' * 542)
        footer_line += pos_h2

        _log.info('FOOTER LINE FIELD     (length %s [651]): %s'
                  % (str(len(footer_line)).zfill(3), footer_line))

        n63_book = (header_line + '\r\n' + bank_lines + footer_line).upper()

        # Send to the file and encode
        payment_file_str = n63_book.encode(
            self.ENCODING_NAME, self.ENCODING_TYPE)

        # Generate filename
        filename = (datetime.today().strftime("%Y%m%d") + 'F' +
                    self.phase + '_' + self.name + ".txt")

        return payment_file_str, filename
