# -*- coding: utf-8 -*-
# Copyright 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json
import base64
from io import StringIO
from odoo import http, _
from odoo.http import request
from odoo.addons.website.controllers.form import WebsiteForm


class WebsiteFormCim(WebsiteForm):

    @http.route()
    def website_form(self, model_name, **kwargs):
        value_to_return = super(WebsiteFormCim, self).website_form(
            model_name, **kwargs)
        if model_name == 'cim.complaint':
            new_id = 0
            new_tracking_code = ''
            response = value_to_return.response
            if response:
                try:
                    response = json.loads(response[0])
                    if 'id' in response and response['id']:
                        new_id = response['id']
                        complaint = request.env['cim.complaint'].sudo().browse(
                            new_id)
                        if complaint:
                            new_tracking_code = \
                                complaint.decrypted_tracking_code
                except Exception:
                    new_id = 0
                    new_tracking_code = ''
            if new_id and new_tracking_code:
                value_to_return = {
                    'id': new_id,
                    'tracking_code_new_complaint': new_tracking_code, }
                value_to_return = json.dumps(value_to_return)
            else:
                value_to_return = json.dumps(False)
        return value_to_return

    def insert_record(self, request, model, values, custom, meta=None):
        if model.model == 'cim.complaint':
            values['complaint_lang'] = request.httprequest.cookies.get(
                'website_lang')
        return super(WebsiteFormCim, self).insert_record(
            request, model, values, custom, meta)

    @http.route('/tracking-code', type='http', auth='public', website=True)
    def show_tracking_code(self, **kwargs):
        tracking_code = 0
        if request.httprequest.method == 'GET':
            tracking_code = request.params.get('code')
        text_to_show = _('(code not available)')
        if tracking_code:
            text_to_show = tracking_code
        return request.render(
            'cim_complaints_channel.trackingcode_page',
            {'tracking_code': text_to_show})

    @http.route('/tracing', type='http', auth='public', website=True)
    def enter_tracking_code(self, **kwargs):
        return request.render(
            'cim_complaints_channel.trackingcode_form', {})

    @http.route('/communications', type='http', auth='public', website=True)
    def show_communications(self, **kwargs):
        communications = None
        model_cim_complaint = request.env['cim.complaint'].sudo()
        entered_complaint = None
        entered_tracking_code = kwargs.get('trackingcode', False)
        if entered_tracking_code:
            complaints = model_cim_complaint.search([], order='id desc')
            for complaint in (complaints or []):
                decrypted_tracking_code_of_complaint = \
                    model_cim_complaint.decrypt_data(
                        complaint.tracking_code,
                        model_cim_complaint._cipher_key)
                if (entered_tracking_code ==
                   decrypted_tracking_code_of_complaint):
                    entered_complaint = complaint
                    break
        if entered_complaint:
            encrypted_tracking_code = model_cim_complaint.encrypt_data(
                entered_tracking_code, model_cim_complaint._cipher_key)
            encrypted_tracking_code_b64 = base64.urlsafe_b64encode(
                encrypted_tracking_code)
            communications = \
                request.env['cim.complaint.communication'].sudo(
                    ).search([('complaint_id', '=', entered_complaint.id),
                              ('state', '=', '02_validated')])
            return request.render(
                'cim_complaints_channel.communications_page',
                {'complaint': entered_complaint,
                 'communications': communications,
                 'encrypted_tracking_code_b64': encrypted_tracking_code_b64})
        else:
            text_to_show = _('Sorry, the code entered is not correct. '
                             'Please, try again.')
            return request.render(
                'cim_complaints_channel.trackingcode_form',
                {'error_message': text_to_show})

    @http.route('/communications/<int:communication_id>', type='http',
                auth='public', website=True)
    def show_communication(self, communication_id=None, **kwargs):
        complaint = None
        communication = None
        model_cim_complaint_communication = \
            request.env['cim.complaint.communication'].sudo()
        if ('m' in kwargs and kwargs['m']):
            complaint = self._get_complaint_from_encrypted_tracking_code(
                kwargs['m'])
            if complaint and communication_id:
                communication = model_cim_complaint_communication.browse(
                    communication_id)
        if (complaint and communication and
           communication.complaint_id == complaint):
            return request.render(
                'cim_complaints_channel.communication_form',
                {'communication': communication,
                 'encrypted_tracking_code_b64': str(kwargs['m'])})
        else:
            text_to_show = _('Sorry, the entered URL is not valid. '
                             'Please, enter the tracking code.')
            return request.render(
                'cim_complaints_channel.trackingcode_form',
                {'error_message': text_to_show})

    def _get_complaint_from_encrypted_tracking_code(
            self, encrypted_tracking_code):
        complaint = None
        if encrypted_tracking_code:
            model_cim_complaint = \
                request.env['cim.complaint'].sudo()
            encrypted_tracking_code_b64 = str(encrypted_tracking_code)
            encrypted_tracking_code_b64 = encrypted_tracking_code_b64 + \
                '=' * (4 - len(encrypted_tracking_code_b64) % 4)
            encrypted_tracking_code = base64.urlsafe_b64decode(
                encrypted_tracking_code_b64)
            decrypted_tracking_code = \
                model_cim_complaint.decrypt_data(
                    encrypted_tracking_code,
                    model_cim_complaint._cipher_key)
            complaints = model_cim_complaint.search([], order='id desc')
            for current_complaint in (complaints or []):
                decrypted_tracking_code_of_complaint = \
                    model_cim_complaint.decrypt_data(
                        current_complaint.tracking_code,
                        model_cim_complaint._cipher_key)
                if (decrypted_tracking_code ==
                   decrypted_tracking_code_of_complaint):
                    complaint = current_complaint
                    break
        return complaint

    @http.route('/communications/download/<int:communication_id>/<int:n_doc>',
                type='http', auth='public', website=True)
    def download_document(self, communication_id=None, n_doc=None, **kwargs):
        complaint = None
        communication = None
        model_cim_complaint = \
            request.env['cim.complaint'].sudo()
        model_cim_complaint_communication = \
            request.env['cim.complaint.communication'].sudo()
        if ('m' in kwargs and kwargs['m']):
            complaint = self._get_complaint_from_encrypted_tracking_code(
                kwargs['m'])
            if communication_id:
                communication = model_cim_complaint_communication.browse(
                    communication_id)
        if (complaint and communication and
           communication.complaint_id == complaint and
           n_doc >= 0 and n_doc <= model_cim_complaint.MAX_DOCUMENTS):
            file_content = None
            if n_doc == 1:
                file_content = StringIO(base64.standard_b64decode(
                    communication.document_01))
                return http.send_file(
                    file_content,
                    filename=communication.document_01_name,
                    as_attachment=True)
            if n_doc == 2:
                file_content = StringIO(base64.standard_b64decode(
                    communication.document_02))
                return http.send_file(
                    file_content,
                    filename=communication.document_02_name,
                    as_attachment=True)
            if n_doc == 3:
                file_content = StringIO(base64.standard_b64decode(
                    communication.document_03))
                return http.send_file(
                    file_content,
                    filename=communication.document_03_name,
                    as_attachment=True)
            if n_doc == 4:
                file_content = StringIO(base64.standard_b64decode(
                    communication.document_04))
                return http.send_file(
                    file_content,
                    filename=communication.document_04_name,
                    as_attachment=True)
            if n_doc == 5:
                file_content = StringIO(base64.standard_b64decode(
                    communication.document_05))
                return http.send_file(
                    file_content,
                    filename=communication.document_05_name,
                    as_attachment=True)
            if n_doc == 6:
                file_content = StringIO(base64.standard_b64decode(
                    communication.document_06))
                return http.send_file(
                    file_content,
                    filename=communication.document_06_name,
                    as_attachment=True)
        else:
            return request.not_found()
