# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import datetime
from odoo import _, models
from odoo.exceptions import UserError


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    # Num of payment: num_of_payment + control digit
    def _calculate_num_of_payment(self, line, num_of_payment):
        converter = self.env['payment.converter.spain']
        id_code = converter.digits_only(line['partner_id'].vat)
        num_of_payment = str(num_of_payment).zfill(7)
        base_number = int(id_code + num_of_payment)
        control_digit = base_number % 7
        num_of_payment = num_of_payment + str(control_digit)  # No space
        return num_of_payment

    def _search_in_payment_lines(self, line):
        found_payment_line = False
        for payment_line in self.payment_line_ids:
            for transaction_line in line.payment_line_ids:
                if payment_line.id == transaction_line.id:
                    found_payment_line = payment_line
        return found_payment_line

    def _start_68(self):
        converter = self.env['payment.converter.spain']
        start_68 = False
        if self.payment_mode_id.initiating_party_identifier:
            start_68 = self.payment_mode_id.initiating_party_identifier
        elif self.payment_mode_id.initiating_party_issuer:
            start_68 = self.payment_mode_id.initiating_party_issuer
        if not start_68:
            raise UserError(
                _('The Transaction Initiator Identifier or Transaction Issuer '
                    'have not been configured.'))
        else:
            start_68 = converter.convert(start_68, 12)
        return start_68

    def _cabecera_ordenante_68(self):
        converter = self.env['payment.converter.spain']
        today = datetime.today().strftime('%d%m%y')
        text = '0359'
        text += self._start_68()
        text += ' ' * 12
        text += '001'
        text += today
        text += ' ' * 9
        if not self.company_partner_bank_id.acc_number:
            raise UserError(
                _('Configuration error:\n\n No account bank number found '
                  'for ordering party: Cabecera ordenante 68'))
        bank_acc_number = self.company_partner_bank_id.acc_number
        bank_acc_number = \
            converter.convert(bank_acc_number.replace(' ', ''), 24)
        text += bank_acc_number
        text += ' ' * 30
        text += '\r\n'
        if len(text) % 102 != 0:
            raise UserError(
                _('Configuration error:\n\nA line in "%s" is not 100 '
                  'characters long:\n%s') % ('Cabecera ordenante 68', text))
        return text

    def _cabecera_beneficiario_68(self, line):
        converter = self.env['payment.converter.spain']
        text = '0659'
        text += self._start_68()
        text += converter.convert(line['partner_id'].vat, 12)
        return text

    def _registro_beneficiario_68(self, line, num_of_payment):
        converter = self.env['payment.converter.spain']
        num_of_payment = self._calculate_num_of_payment(line, num_of_payment)
        text = ''

        # Get address
        address = None
        partner = self.env['res.partner']
        address_ids = line['partner_id'].address_get(['default', 'invoice'])
        if address_ids.get('invoice'):
            address = partner.browse(address_ids.get('invoice'))
        elif address_ids.get('default'):
            address = partner.browse(address_ids.get('default'))
        else:
            raise UserError(
                _('User error:\n\nPartner %s has no invoicing or '
                  'default address.') % line['partner_id'].name)

        # Primer tipo
        text1 = self._cabecera_beneficiario_68(line)
        text1 += '010'
        text1 += converter.convert(line['partner_id'].name[:40], 40)
        text1 += ' ' * 29
        text1 += '\r\n'
        if len(text1) % 102 != 0:
            raise UserError(
                _('Configuration error:\n\nA line in "%s" is not 100 '
                  'characters long:\n%s') %
                ('Beneficiary record, type 1', text))
        text += text1

        # Segundo tipo
        text2 = self._cabecera_beneficiario_68(line)
        text2 += '011'
        txt_address = ''
        if address.street:
            txt_address += address.street
        if address.street2:
            txt_address += ' ' + address.street2
        text2 += converter.convert(txt_address[:45], 45)
        text2 += ' ' * 24
        text2 += '\r\n'
        if len(text2) % 102 != 0:
            raise UserError(
                _('Configuration error:\n\nA line in "%s" is not 100 '
                  'characters long:\n%s') %
                ('Beneficiary record, type 2', text))
        text += text2

        # Tercer tipo
        text3 = self._cabecera_beneficiario_68(line)
        text3 += '012'
        text3 += converter.convert(address.zip, 5)
        text3 += converter.convert(address.city[:40], 40)
        text3 += ' ' * 24
        text3 += '\r\n'
        if len(text3) % 102 != 0:
            raise UserError(
                _('Configuration error:\n\nA line in "%s" is not 100 '
                  'characters long:\n%s') %
                ('Beneficiary record, type 3', text))
        text += text3

        # Cuarto tipo
        text4 = self._cabecera_beneficiario_68(line)
        text4 += '013'
        text4 += converter.convert(address.zip, 9)
        text4 += converter.convert(address.state_id.name[:30] or '', 30)
        text4 += converter.convert(address.country_id.name[:20] or '', 20)
        text4 += ' ' * 10
        text4 += '\r\n'
        if len(text4) % 102 != 0:
            raise UserError(
                _('Configuration error:\n\nA line in "%s" is not 100 '
                  'characters long:\n%s') %
                ('Beneficiary record, type 4', text))
        text += text4

        # Quinto tipo
        text5 = self._cabecera_beneficiario_68(line)
        text5 += '014'
        text5 += num_of_payment
        if 'date' in line:
            date_pago = line['date']
        else:
            date_pago = datetime.today()

        text5 += converter.convert(date_pago.strftime('%d%m%Y'), 8)
        text5 += converter.convert(abs(line['amount']), 12)
        text5 += '0'
        country_code = address.country_id and address.country_id.code or ''
        if country_code != 'ES':
            text5 += country_code  # 2
        else:
            text5 += ' ' * 2
        text5 += ' ' * 6
        text5 += ' ' * 32
        text5 += '\r\n'
        if len(text5) % 102 != 0:
            raise UserError(
                _('Configuration error:\n\nA line in "%s" is not 100 '
                  'characters long:\n%s') %
                ('Beneficiary record, type 5', text))
        text += text5

        # Sexto tipo
        text6 = self._cabecera_beneficiario_68(line)
        text6 += '015'
        text6 += num_of_payment  # 8 spaces (not used)
        payment_line = self._search_in_payment_lines(line)
        if payment_line:
            ref_payment = converter.convert(payment_line['communication'], 12)
            communication = \
                converter.convert(payment_line['communication'], 26)
        else:
            ref_payment = ' ' * 12
            communication = ' ' * 26
        text6 += ref_payment  # Repeat
        self.date_generated = datetime.today()  # Set generated_date
        date_create = \
            converter.convert(self.date_generated.strftime('%d%m%Y'), 8)
        text6 += date_create
        text6 += converter.convert(abs(line['amount']), 12)
        text6 += 'H'
        text6 += communication
        text6 += ' ' * 2
        text6 += '\r\n'
        if len(text6) % 102 != 0:
            raise UserError(
                _('Configuration error:\n\nA line in "%s" is not 100 '
                  'characters long:\n%s') %
                ('Beneficiary record, type 6', text))
        text += text6

        return text

    def _total_general_68(self, total_payments, total_amount):
        converter = self.env['payment.converter.spain']
        text = '0859'
        text += self._start_68()
        text += ' ' * 12
        text += ' ' * 3
        text += converter.convert(abs(total_amount), 12)
        text += converter.convert(abs(total_payments * 6 + 2), 10)
        text += ' ' * 42
        text += ' ' * 5
        text += '\r\n'
        if len(text) % 102 != 0:
            raise UserError(
                _('Configuration error:\n\nA line in "%s" is not 100 '
                  'characters long:\n%s') %
                ('Registration of totals', text))
        return text

    def generate_payment_file(self):
        """Creates the CSB Direct Debit file"""
        self.ensure_one()
        if self.payment_method_id.code != "csb_direct_debit_payments":
            return super().generate_payment_file()

        # Vars
        txt_file = ''
        num_of_payment = 0
        total_payments = 0
        total_amount = 0.0

        # Header
        txt_file += self._cabecera_ordenante_68()

        # Beneficiary records
        for line in self.payment_ids:
            num_of_payment += 1
            txt_file += self._registro_beneficiario_68(line, num_of_payment)
            total_payments += 1
            total_amount += abs(line['amount'])
        txt_file += self._total_general_68(total_payments, total_amount)

        filename = self.name.replace('/', '_')
        filename += datetime.today().strftime('%d-%m-%Y') + '.txt'
        txt_bin = txt_file.encode()
        return (txt_bin, filename)
