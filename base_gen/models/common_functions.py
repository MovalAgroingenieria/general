# 2022 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import base64
import datetime
import pytz
from Crypto.Cipher import AES
from odoo import models


class CommonFunctions(models.AbstractModel):
    _name = 'common.functions'
    _description = 'Common functions to be used by other models'

    def transform_float_to_locale(self, float_number, precision, lang=False):
        precision = '%.' + str(precision) + 'f'
        if (not lang):
            lang = 'es_ES'
            if ('lang' in self.env.context and self.env.context['lang']):
                lang = self.env.context['lang']
        lang_model = self.env['res.lang'].search([('code', '=', lang)])
        formated_float_number = str(float_number)
        if (lang_model):
            formated_float_number = \
                lang_model.format(precision, float_number, True)
        return formated_float_number

    def transform_date_to_locale(self, date, lang=False):
        if (not lang):
            lang = 'es_ES'
            if ('lang' in self.env.context and self.env.context['lang']):
                lang = self.env.context['lang']
        lang_model = self.env['res.lang'].search([('code', '=', lang)])
        formated_date_str = str(date)
        if (lang_model):
            formated_date_str = date.strftime(lang_model.date_format)
        return formated_date_str

    def get_value_from_translation(self, module, src, lang=None):
        resp = src
        if not lang:
            lang = self.env.context.get('lang')
        filtered_translations = self.sudo().env['ir.translation'].search(
            [('lang', '=', lang), ('module', '=', module), ('src', '=', src)])
        if filtered_translations:
            resp = filtered_translations[0].value
        return resp

    # Encrypt data in format param1-param2-param3 With cipher_key supplied
    def encrypt_data(self, params, cipher_key):
        credentials = '-'.join(params)
        credentials = credentials.ljust(32)
        current_datetime = pytz.utc.localize(datetime.datetime.now())
        current_datetime = current_datetime.astimezone(
            pytz.timezone('Europe/Madrid'))
        current_datetime = str(current_datetime)[:16].replace(' ', 'T')
        minimum = int(current_datetime[14:])
        if minimum < 30:
            minimum = '00'
        else:
            minimum = '30'
        iv = current_datetime[:14] + minimum
        aes_encryptor = AES.new(cipher_key, AES.MODE_CBC, iv)
        cipher_text = aes_encryptor.encrypt(credentials)
        cipher_text = base64.b64encode(cipher_text).decode('utf-8')
        return cipher_text
