# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json
import logging

import requests
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend


from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.base.models.res_bank import sanitize_account_number

_logger = logging.getLogger(__name__)

BANKINPLAY_ENDPOINT = 'https://app.bankinplay.com/intradia-core'


class BankinplayInterface(models.AbstractModel):
    _name = 'bankinplay.interface'
    _description = 'Interface to all interactions with Bankinplay API'

    def _decrypt_bankinplay_data(self, data, key, iv):
        key_size = 16
        iv_size = 16
        padding_char = '$'
        key = key.ljust(key_size, padding_char)[:key_size]
        iv = iv.ljust(iv_size, padding_char)[:iv_size]
        backend = default_backend()
        cipher = Cipher(algorithms.AES(key.encode()), modes.CBC(iv.encode()),
                        backend=backend)
        decryptor = cipher.decryptor()
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        decrypted_data = decryptor.update(base64.b64decode(data)) + \
            decryptor.finalize()
        decrypted_data = unpadder.update(decrypted_data) + unpadder.finalize()
        return json.loads(decrypted_data.decode('utf-8'))

    def _login(self, username, password):
        '''Bankinplay login returns an access token for further requests.'''
        url = BANKINPLAY_ENDPOINT + '/clienteApi/jwt_token'
        if not (username and password):
            raise UserError(_('Please fill login and key.'))
        login_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        _logger.debug(_('POST request on %s'), url)
        response = requests.post(
            url,
            params={
                'user': username,
                'pass': password},
            headers=login_headers,
        )
        data = self._get_response_data(response)
        access_token = data.get('access_token', False)
        if not access_token:
            raise UserError(_('Bankinplay : no token'))
        return {
            'access_token': access_token,
            'username': username,
            'password': password,
        }

    def _get_request_headers(self, access_data):
        '''Get headers with authorization for further bankinplay requests.'''
        return {
            'Accept': 'application/json',
            'Authorization': 'Bearer %s' % access_data['access_token'],
        }

    def _get_request_headers_remote(self):
        '''Get headers with authorization for remote endpoint requests.'''
        return {
            'Accept': 'application/json',
        }

    def _set_access_account(self, access_data, account_number):
        '''Set bankinplay account for bank account in access_data.'''
        url = BANKINPLAY_ENDPOINT + '/api/v2/entidad/cuentaBancaria'
        data = self._get_request(access_data, url, {})
        for bankinplay_account in data.get('data', []):
            bankinplay_iban = sanitize_account_number(
                bankinplay_account.get('cuentaCompleta', '')
            )
            if bankinplay_iban == account_number:
                access_data['bankinplay_account'] = bankinplay_account.get(
                    'id')
                return
        # If we get here, we did not find Bankinplay account for bank account.
        raise UserError(
            _('Bankinplay : wrong configuration, account %s not found in %s')
            % (account_number, data)
        )

    def _set_close_movements_callback(
            self, access_data, date_since, date_until):
        '''Set the info that will be posted and then a callback will fill,
        '''
        url = BANKINPLAY_ENDPOINT + '/api/v1/statement/lectura_cierre'
        params = {
            'fechaDesdeOperacion': date_since.strftime('%d/%m/%Y'),
            'fechaHastaOperacion': date_until.strftime('%d/%m/%Y'),
            'cuentasBancarias': [access_data['bankinplay_account']],
            'exportados': True,
        }
        data = self._post_request(access_data, url, params)
        signature = data.get('signature', '')
        response_id = data.get('responseId', '')
        return {
            'bankinplay_signature': signature,
            'bankinplay_responseid': response_id,
            'bankinplay_date_since': date_since,
            'bankinplay_date_until': date_until,
        }

    def _set_close_movements_callback_remote_endpoint(
            self, date_since, date_until, endpoint_url, bankinplay_account):
        '''Set the info that will be posted and then a callback will fill,
        '''
        url = endpoint_url
        return_url = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url')
        params = {
            'date_since': date_since.strftime('%d/%m/%Y'),
            'date_until': date_until.strftime('%d/%m/%Y'),
            'bankinplay_account': [bankinplay_account],
            'return_url': return_url,
        }
        data = self._post_request_remote(url, params)
        signature = data.get('signature', '')
        response_id = data.get('response_id', '')
        return {
            'bankinplay_signature': signature,
            'bankinplay_responseid': response_id,
            'bankinplay_date_since': date_since,
            'bankinplay_date_until': date_until,
        }

    def _post_request(self, access_data, url, params):
        '''Interact with Bankinplay to get data.'''
        headers = self._get_request_headers(access_data)
        _logger.debug(
            _('POST request to %s with headers %s and params %s'), url, params,
            headers
        )
        response = requests.post(url, params=params, headers=headers)
        response_parsed = self._get_response_data(response)
        # Check if response is cipher for V2 of the API
        if (response_parsed.get('signature', False) and
                response_parsed.get('data', False)):
            response_parsed['data'] = self._decrypt_bankinplay_data(
                response_parsed.get('data', False),
                access_data.get('username', False),
                access_data.get('password', False),)
        return response_parsed

    def _post_request_remote(self, url, params):
        '''Interact with Remote Endpoint to get data.'''
        headers = self._get_request_headers_remote()
        _logger.debug(
            _('POST request to %s with headers %s and params %s'), url, params,
            headers
        )
        response = requests.post(url, json=params, headers=headers)
        response_parsed = self._get_response_data(response)
        response_parsed = response_parsed.get('result', {})
        return response_parsed

    def _get_request(self, access_data, url, params):
        '''Interact with Bankinplay to get data.'''
        headers = self._get_request_headers(access_data)
        _logger.debug(
            _('GET request to %s with headers %s and params %s'), url, params,
            headers
        )
        response = requests.get(url, params=params, headers=headers)
        response_parsed = self._get_response_data(response)
        # Check if response is cipher for V2 of the API
        if (response_parsed.get('signature', False) and
                response_parsed.get('data', False)):
            response_parsed['data'] = self._decrypt_bankinplay_data(
                response_parsed.get('data', False),
                access_data.get('username', False),
                access_data.get('password', False),)
        return response_parsed

    def _get_response_data(self, response):
        '''Get response data for GET or POST request.'''
        _logger.debug(_('HTTP answer code %s from Bankinplay'),
                      response.status_code)
        if response.status_code not in (200, 201):
            raise UserError(
                _('Server returned status code %s: %s')
                % (response.status_code, response.text)
            )
        response_data = json.loads(response.text)
        return response_data

    def _register_bankinplay_callbacks(self, access_data, endpoint_url):
        # event_list = [
        #   'lectura_intradia',
        #   'lectura_cierre',
        #   'lectura_tarjeta',
        #   'asiento_contable',
        #   'exportacion_conciliacion',
        #   'exportacion_conciliacion_terceros',
        # ]
        url = BANKINPLAY_ENDPOINT + '/api/v1/callback'
        endpoint_hook_url = f'{endpoint_url}/webhook/bankinplay_callback'
        params = {
            "event": "lectura_cierre",
            "target": endpoint_hook_url
        }
        data = self._post_request(access_data, url, params)
        return data
