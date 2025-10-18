# -*- coding: utf-8 -*-
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

        Args:
            company: res.company record with verifacti configuration
            invoice: account.invoice record to send
        """
        try:
            # Prepare invoice data
            invoice_data = invoice._prepare_verifacti_data()

            # API endpoint
            url = "{}/verifactu/create".format(company.verifacti_api_url)

            # Headers
            headers = {
                'Authorization': 'Bearer {}'.format(company.verifacti_api_key),
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            # Make the request
            response = requests.post(
                url,
                headers=headers,
                json=invoice_data,
                timeout=30
            )

            # Process response
            if response.status_code == 200:
                response_data = response.json()

                # Get QR code from response (already in base64 from API)
                qr_code = response_data.get('qr', '')

                # Get URL from response
                verifacti_url = response_data.get('url', '')

                return {
                    'success': True,
                    'id': response_data.get('uuid'),
                    'qr_code': qr_code,
                    'url': verifacti_url,
                    'response': response_data
                }
            else:
                error_msg = "API Error: {}".format(response.status_code)
                error_data = {}
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', error_msg)
                except:
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

            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()

            return img_str
        except Exception:
            return False
