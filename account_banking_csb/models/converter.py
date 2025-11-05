# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api, _
from odoo.exceptions import UserError


class PaymentConverterSpain(models.Model):
    _name = 'payment.converter.spain'
    _description = "Payment converter for Spain"

    @api.model
    def digits_only(self, cc_in):
        """Discards non-numeric chars"""
        cc = ""
        for i in cc_in or '':
            try:
                int(i)
                cc += i
            except ValueError:
                pass
        return cc

    @api.model
    def to_ascii(self, text):
        """Converts special characters such as those with accents to their
        ASCII equivalents"""
        old_chars = ['á', 'é', 'í', 'ó', 'ú', 'à', 'è', 'ì', 'ò', 'ù', 'ä',
                     'ë', 'ï', 'ö', 'ü', 'â', 'ê', 'î', 'ô', 'û', 'Á', 'É',
                     'Í', 'Ú', 'Ó', 'À', 'È', 'Ì', 'Ò', 'Ù', 'Ä', 'Ë', 'Ï',
                     'Ö', 'Ü', 'Â', 'Ê', 'Î', 'Ô', 'Û', 'ñ', 'Ñ', 'ç', 'Ç',
                     'ª', 'º', '·', '\n']
        new_chars = ['a', 'e', 'i', 'o', 'u', 'a', 'e', 'i', 'o', 'u', 'a',
                     'e', 'i', 'o', 'u', 'a', 'e', 'i', 'o', 'u', 'A', 'E',
                     'I', 'U', 'O', 'A', 'E', 'I', 'O', 'U', 'A', 'E', 'I',
                     'O', 'U', 'A', 'E', 'I', 'O', 'U', 'n', 'N', 'c', 'C',
                     'a', 'o', '.', ' ']
        for old, new in zip(old_chars, new_chars):
            text = text.replace(old, new)
        return text

    @api.model
    def convert_text(self, text, size, justified='left'):
        if justified == 'left':
            return self.to_ascii(text)[:size].ljust(size)
        else:
            return self.to_ascii(text)[:size].rjust(size)

    @api.model
    def convert_float(self, number, size):
        text = str(int(round(number * 100, 0)))
        if len(text) > size:
            raise UserError(
                _('Error:\n\nCan not convert float number %(number).2f '
                    'to fit in %(size)d characters.') % {
                    'number': number, 'size': size})
        return text.zfill(size)

    @api.model
    def convert_int(self, number, size):
        text = str(number)
        if len(text) > size:
            raise UserError(
                _('Error:\n\nCan not convert integer number %(number)d '
                    'to fit in %(size)d characters.') % {
                    'number': number, 'size': size})
        return text.zfill(size)

    @api.model
    def convert(self, value, size, justified='left'):
        if not value:
            return self.convert_text('', size)
        elif isinstance(value, float):
            return self.convert_float(value, size)
        elif isinstance(value, int):
            return self.convert_int(value, size)
        else:
            return self.convert_text(value, size, justified)

    @api.model
    def convert_bank_account(self, value, partner_name):
        if not isinstance(value):
            raise UserError(
                _('User error:\n\nThe bank account number of %s is not '
                    'defined.') % partner_name)
        ccc = self.digits_only(value)
        if len(ccc) != 20:
            raise UserError(
                _('User error:\n\nThe bank account number of %s does not '
                    'have 20 digits.') % partner_name)
        return ccc

    @api.model
    def bank_account_parts(self, value, partner_name):
        if not isinstance(value):
            raise UserError(
                _('User error:\n\nThe bank account number of %s is not '
                    'defined.') % partner_name)
        ccc = self.digits_only(value)
        if len(ccc) != 20:
            raise UserError(
                _('User error:\n\nThe bank account number of %s does not '
                    'have 20 digits.') % partner_name)
        return {'bank': ccc[:4], 'office': ccc[4:8], 'dc': ccc[8:10],
                'account': ccc[10:]}
