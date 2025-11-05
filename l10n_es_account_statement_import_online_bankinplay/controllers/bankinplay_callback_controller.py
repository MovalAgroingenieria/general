# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import http
from odoo.http import request
import json
import requests
from datetime import datetime


class BankinplayCallbackController(http.Controller):
    @http.route(
        '/webhook/bankinplay_callback', type='json', auth='public',
        methods=['POST'], csrf=False)
    def handle_bankinplay_callback(self, **kw):
        json_data = request.jsonrequest
        # Get JSON and check if its a Close reading, which are the only one
        # handled yet
        if ('responseId' in json_data and 'signature' in json_data and
                'triggered_event' in json_data and
                json_data['triggered_event'] == 'lectura_cierre'):
            import_statement = request.env['account.bank.statement'].sudo().\
                search([
                    ('bankinplay_responseid', '=', json_data['responseId']),
                    ('bankinplay_signature', '=', json_data['signature']),
                ])
            # If statement already created,
            if (import_statement):
                import_statement.journal_id.online_bank_statement_provider_id.\
                    _bankinplay_update_statement_data_after_callback(
                        import_statement, json_data['data'])
            else:
                # Check if on remote database and in that case redirect
                # the response
                remote_response = request.env['bankinplay.response'].sudo().\
                    search([
                        ('bankinplay_responseid', '=',
                            json_data['responseId']),
                        ('bankinplay_signature', '=', json_data['signature']),
                    ])
                if (remote_response):
                    # Send the data decrypted to endppoint database
                    interface_model = request.env['bankinplay.interface'].\
                        sudo()
                    bankinplay_api_key = request.env['ir.config_parameter'].\
                        sudo().get_param(
                        'l10n_es_account_statement_import_online_bankinplay'
                        '.bankinplay_integration_api_key')
                    bankinplay_api_secret = request.env[
                        'ir.config_parameter'].sudo().get_param(
                        'l10n_es_account_statement_import_online_bankinplay'
                        '.bankinplay_integration_api_secret')
                    json_data['data'] = interface_model.\
                        _decrypt_bankinplay_data(
                            json_data['data'], bankinplay_api_key,
                            bankinplay_api_secret)
                    url = remote_response.endpoint_return_url + \
                        '/webhook/bankinplay_callback'
                    requests.post(url, json=json_data, headers={
                        'Accept': 'application/json',
                    })
                    remote_response.bankinplay_response = json.dumps(json_data)
                    # remote_response.unlink()

    @http.route(
        '/remote/bankinplay_callback', type='json', auth='public',
        methods=['POST'], csrf=False)
    def handle_remote_bankinplay_callback(self, **kwargs):
        params = request.jsonrequest
        date_since = datetime.strptime(params['date_since'], '%d/%m/%Y')
        date_until = datetime.strptime(params['date_until'], '%d/%m/%Y')
        bankinplay_account = params['bankinplay_account'][0]
        return_url = params['return_url']
        interface_model = request.env['bankinplay.interface'].sudo()
        bankinplay_api_key = request.env['ir.config_parameter'].sudo().\
            get_param(
            'l10n_es_account_statement_import_online_bankinplay'
            '.bankinplay_integration_api_key')
        bankinplay_api_secret = request.env['ir.config_parameter'].\
            sudo().get_param(
            'l10n_es_account_statement_import_online_bankinplay'
            '.bankinplay_integration_api_secret')
        try:
            access_data = interface_model._login(
                bankinplay_api_key, bankinplay_api_secret)
            interface_model._set_access_account(
                access_data, bankinplay_account)
            response_data = interface_model._set_close_movements_callback(
                access_data, date_since, date_until)
            signature = response_data.get('bankinplay_signature')
            response_id = response_data.get('bankinplay_responseid')
            request.env['bankinplay.response'].sudo().create({
                'bankinplay_signature': signature,
                'bankinplay_responseid': response_id,
                'endpoint_return_url': return_url,
            })
            return {
                'signature': signature,
                'response_id': response_id,
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
