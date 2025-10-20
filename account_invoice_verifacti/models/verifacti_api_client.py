# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import requests
import qrcode
import io
import base64
from odoo import models, _


class VerifactiApiClient(models.AbstractModel):
    _name = 'verifacti.api.client'
    _description = 'Verifacti API Client'

    def send_invoice(self, company, invoice):
        """Send invoice to Verifacti API
        """
        try:
            invoice_data = invoice._prepare_verifacti_data()

            url = "{}/verifactu/create".format(company.verifacti_api_url)

            headers = {
                'Authorization': 'Bearer {}'.format(company.verifacti_api_key),
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            response = requests.post(
                url,
                headers=headers,
                json=invoice_data,
                timeout=30
            )

            if response.status_code == 200:
                response_data = response.json()

                qr_data = response_data.get('qr', '')
                verifacti_url = response_data.get('url', '')

                qr_code_binary = None
                if qr_data:
                    if qr_data.startswith('http'):
                        try:
                            qr_response = requests.get(qr_data, timeout=10)
                            if qr_response.status_code == 200:
                                qr_code_binary = base64.b64encode(qr_response.content).decode()
                        except Exception:
                            pass
                    else:
                        try:
                            base64.b64decode(qr_data)
                            qr_code_binary = qr_data
                        except Exception:
                            qr_code_binary = self._generate_qr_code(qr_data)

                return {
                    'success': True,
                    'id': response_data.get('uuid'),
                    'qr_code': qr_code_binary,
                    'url': verifacti_url,
                    'response': response_data
                }
            else:
                error_msg = "API Error: {}".format(response.status_code)
                error_data = {}
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', error_msg)
                except Exception:
                    error_msg = response.text

                return {
                    'success': False,
                    'error': error_msg,
                    'response': error_data if error_data else {'status_code': response.status_code, 'error': error_msg}
                }

        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': "Connection error: {}".format(str(e))
            }
        except Exception as e:
            return {
                'success': False,
                'error': "Unexpected error: {}".format(str(e))
            }

    def check_invoice_status(self, company, verifacti_id):
        """
        Check status of an invoice in Verifacti
        """
        try:
            url = "{}/verifactu/status?uuid={}".format(company.verifacti_api_url, verifacti_id)

            headers = {
                'Authorization': 'Bearer {}'.format(company.verifacti_api_key),
                'Accept': 'application/json'
            }

            response = requests.get(
                url,
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                response_data = response.json()

                state = response_data.get('estado', 'Pending')

                if state == 'Correcto':
                    status = 'accepted'
                elif state in ['Rechazado', 'Duplicado']:
                    status = 'rejected'
                elif state in ['Pendiente', 'Procesando']:
                    status = 'processing'
                else:
                    status = 'sent'

                qr_data = response_data.get('qr', '')
                verifacti_url = response_data.get('url', '')
                qr_code_binary = None
                if qr_data:
                    if qr_data.startswith('http'):
                        try:
                            qr_response = requests.get(qr_data, timeout=10)
                            if qr_response.status_code == 200:
                                qr_code_binary = base64.b64encode(qr_response.content).decode()
                        except Exception:
                            pass
                    else:
                        try:
                            base64.b64decode(qr_data)
                            qr_code_binary = qr_data
                        except Exception:
                            qr_code_binary = self._generate_qr_code(qr_data)

                return {
                    'success': True,
                    'status': status,
                    'qr_code': qr_code_binary,
                    'url': verifacti_url,
                    'response': response_data
                }
            elif response.status_code == 404:
                return {
                    'success': False,
                    'error': 'Invoice not found in Verifacti',
                    'response': {'status_code': 404}
                }
            else:
                error_msg = "API Error: {}".format(response.status_code)
                error_data = {}
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', error_msg)
                except Exception:
                    error_msg = response.text

                return {
                    'success': False,
                    'error': error_msg,
                    'response': error_data if error_data else {'status_code': response.status_code, 'error': error_msg}
                }

        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': "Connection error: {}".format(str(e))
            }
        except Exception as e:
            return {
                'success': False,
                'error': "Unexpected error: {}".format(str(e))
            }

    def _generate_qr_code(self, qr_data):
        """Generate QR code from data"""
        if not qr_data:
            return False

        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            buffer = io.BytesIO()
            img.save(buffer, 'PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()

            return img_str
        except Exception:
            return False
