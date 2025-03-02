# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import json
import requests
import re
from odoo import api, models, exceptions, _


class SmsApi(models.AbstractModel):
    _inherit = 'sms.api'

    @api.model
    def _send_sms(self, numbers, message):
        params = {
            'numbers': numbers,
            'message': message,
        }
        send_mode="single"
        sms_service_set = self.env['ir.config_parameter'].sudo().get_param(
            'sms_alternatives.sms_service')
        if sms_service_set == 'odoo_service':
            service_api = self._contact_iap('/iap/message_send', params)
        elif sms_service_set == 'wausms_service':
            service_api = self._contact_wausms(send_mode, params)
        else:
            raise exceptions.ValidationError(
                _('SMS service %s not found.') % sms_service_set)
        return service_api

    @api.model
    def _send_sms_batch(self, messages):
        params = {'messages': messages}
        send_mode="batch"
        sms_service_set = self.env['ir.config_parameter'].sudo().get_param(
            'sms_alternatives.sms_service')
        if sms_service_set == 'odoo_service':
            service_api = self._contact_iap('/iap/sms/2/send', params)
        elif sms_service_set == 'wausms_service':
            service_api = self._contact_wausms(send_mode, params)
        else:
            raise exceptions.ValidationError(
                _('SMS service %s not found.') % sms_service_set)
        return service_api

    @api.model
    def _contact_wausms(self, send_mode, params):
        headers = ""
        service_url = self.env['ir.config_parameter'].sudo().get_param(
            'sms_wausms.wausms_service_url')
        service_user = self.env['ir.config_parameter'].sudo().get_param(
            'sms_wausms.wausms_service_api_user')
        service_passwd = self.env['ir.config_parameter'].sudo().get_param(
            'sms_wausms.wausms_service_api_passwd')
        sender = self.env['ir.config_parameter'].sudo().get_param(
            'sms_wausms.wausms_service_sender')
        if not service_url or not service_user or not service_passwd \
                or not sender:
            raise exceptions.ValidationError(
                _('Not all WauSMS config parameters have been set.'))
        else:
            credentials = base64.b64encode(
                bytes(service_user.encode('utf-8')) +
                bytes(':'.encode('utf-8')) +
                bytes(service_passwd.encode('utf-8')))
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': 'Basic '+ credentials.decode('utf-8'),
            }
        if send_mode == "single":
            response = self.wausms_response_single(
                service_url=service_url, sender=sender, headers=headers,
                params=params)
        elif send_mode == "batch":
            response = self.wausms_response_batch(
                service_url=service_url, sender=sender, headers=headers,
                params=params)
        return response

    def wausms_response_single(self, service_url, sender, headers, params):
        # TODO: Implement this method. Only used in project and project task
        """
        :param numbers: list of E164 formatted phone numbers
        :param message: content to send
            params = {
                'numbers': numbers,
                'message': message,
            }
        """
        response = _('Not implemented yet')
        return response

    def wausms_response_batch(self, service_url, sender, headers, params):
        """
        :param messages: list of SMS to send, structured as dict [{
            'res_id':  integer: ID of sms.sms,
            'number':  string: E164 formatted phone number,
            'content': string: content to send
        }]
        :batch_response: list of dicts with results
        """
        batch_response = []
        for message in params['messages']:
            # Set vars
            state = 'outgoing'
            response_raw = False
            response = False
            # Get data from message
            res_id = message['res_id']
            number = message['number']
            content = message['content']
            # Get curren SMS
            current_sms = self.env['sms.sms'].browse(res_id)
            # Number of sms
            encoding = self._extract_encoding(content)
            num_char = len(content)
            num_sms = self._count_sms(num_char, encoding)
            # Data to json
            data_raw = {
                'to': [number],
                'text': content,
                'from': sender,
                'coding': encoding,
                'parts': num_sms,
            }
            data = json.dumps(data_raw)
            # Send and catch raw response
            try:
                response_raw = requests.post(
                    service_url, headers=headers, data=data)
                state = self._check_sms_state(response_raw.status_code)
                if 'error' in response_raw.text:
                    wausms_response = json.loads(
                        response_raw.text)['error']['description']
                else:
                    wausms_response = response_raw.content
            except requests.exceptions as requests_error:
                state = 'error'
                wausms_response = "Error requests: %s" % requests_error
            # Create response
            if response_raw.text:
                response = {
                    'res_id': res_id,
                    'state': state,
                    'credit': 0,
                    'wausms_response': wausms_response,
                }
            # Add response to batch_response and wausms data to sms_sms
            if response:
                batch_response.append(response)
                current_sms.write({
                    'wausms_response': wausms_response
                })
        return batch_response

    def _extract_encoding(self, content):
        encoding = 'utf-16'
        gsm7_pattern = re.compile(
            r"^[@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ "
            r"!\"#¤%&'()*+,-./0123456789:;<=>?¡"
            r"ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿"
            r"abcdefghijklmnopqrstuvwxyzäöñüà]*$")
        if gsm7_pattern.match(str(content)):
            encoding = 'gsm'
        return encoding

    def _count_sms(self, num_char, encoding):
        if num_char == 0:
            return 0
        if encoding == 'utf-16':
            if num_char <= 70:
                return 1
            return -(-num_char // 67)
        if num_char <= 160:
            return 1
        return -(-num_char // 153)

    def _check_sms_state(self, response_code):
        sms_state = ""
        if response_code == 202:
            sms_state = 'success'
        elif response_code == 207:
            sms_state = 'success'
        elif response_code == 400:
            sms_state = 'bad_request'
        elif response_code == 401:
            sms_state = 'unregistered'
        elif response_code == 402:
            sms_state = 'insufficient_credit'
        elif response_code == 500:
            sms_state = 'server_error'
        else:
            sms_state = 'server_error'
        return sms_state
