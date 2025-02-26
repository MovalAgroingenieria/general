# -*- coding: utf-8 -*-
# Copyright 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import http, _, fields, tools
from odoo.http import request
from odoo.addons.eom_authdnie.controllers.main import WebsiteEom
from io import StringIO
import pytz
import base64


class WebsiteEOffice(WebsiteEom):

    def get_user_info(self, kwargs):
        identif_token = ''
        model_digitalregister = request.env['eom.digitalregister'].sudo()
        user_info = False
        if request.httprequest.method == 'POST':
            identif_token = kwargs.get('identif_token', False)
            if identif_token:
                plain_text = model_digitalregister.decrypt_data(identif_token)
                if plain_text:
                    (country, dni, firstname, lastname,
                     authority) = model_digitalregister.\
                        get_items_of_decrypted_identif(plain_text)
                    if all([country, dni, firstname, lastname, authority]):
                        dni_full = country + dni
                        digitalregister = model_digitalregister.search(
                            [('name', '=', dni_full)], limit=1)
                        identif_header = '%s, %s (%s)' % (
                            lastname, firstname, dni_full)
                        user_info = {
                            'country': country,
                            'dni': dni_full,
                            'firstname': firstname,
                            'lastname': lastname,
                            'authority': authority,
                            'identif_token': identif_token,
                            'digitalregister': digitalregister,
                            'identif_header': identif_header,
                        }
        return user_info

    def transform_time_to_locale(self, time, digitalregister=None):
        formated_date_str = None
        if (time):
            lang = 'es_ES'
            tz = 'Europe/Madrid'
            if digitalregister and digitalregister.partner_id:
                if digitalregister.partner_id.tz:
                    tz = digitalregister.partner_id.tz
                if digitalregister.partner_id.lang:
                    lang = digitalregister.partner_id.lang
            utc_time = fields.Datetime.from_string(time)
            local_timezone = pytz.timezone(tz)
            local_time = pytz.utc.localize(utc_time).astimezone(local_timezone)
            lang_model = request.env['res.lang'].sudo().search(
                [('code', '=', lang)])
            formated_date_str = local_time.strftime(
                lang_model.date_format + u' ' + lang_model.time_format)
        return formated_date_str

    def format_communication(self, communication, digitalregister):
        communication_model = request.env[
            'eom.electronicfile.communication'].sudo()
        attachment_model = request.env['ir.attachment'].sudo()
        attachments = attachment_model.search(
            [('res_model', '=', 'eom.electronicfile.communication'),
                ('res_id', '=', communication.id)],
        ).mapped(lambda x: {
            'id': x.id,
            'name': x.name,
        })
        return {
            'id': communication.id,
            'electronicfile_id': communication.electronicfile_id.id,
            'issue': communication.issue,
            'communication_text': tools.html2plaintext(
                communication.communication_text).strip(),
            'is_notification': communication.is_notification,
            'name': communication.name,
            'state': communication_model._fields['state'].
            convert_to_export(communication.state, communication),
            'state_key': communication.state,
            'document': False,
            'document_name': False,
            'validation_time': self.transform_time_to_locale(
                communication.validation_time, digitalregister),
            'notification_deadline_date': self.transform_time_to_locale(
                communication.notification_deadline_date, digitalregister),
            'reading_time': self.transform_time_to_locale(
                communication.reading_time, digitalregister),
            'rejection_time': self.transform_time_to_locale(
                communication.rejection_time, digitalregister),
            'attachments': attachments,
        }

    def format_efile(self, efile, digitalregister):
        efiles_model = request.env['eom.electronicfile'].sudo()
        attachment_model = request.env['ir.attachment'].sudo()
        communications = efile.communication_ids.filtered(
            lambda x: x.state != '01_draft'
        ).mapped(lambda x: self.format_communication(x, digitalregister))
        attachments = attachment_model.search(
            [('res_model', '=', 'eom.electronicfile'),
                ('res_id', '=', efile.id)],
        ).mapped(lambda x: {
            'id': x.id,
            'name': x.name,
        })
        return {
            'id': efile.id,
            'name': efile.name,
            'event_time': self.transform_time_to_locale(
                efile.event_time, digitalregister),
            'type': efiles_model._fields['type'].
            convert_to_export(efile.type, efile),
            'type_key': efile.type,
            'state': efiles_model._fields['state'].
            convert_to_export(efile.state, efile),
            'state_key': efile.state,
            'exposition': efile.exposition,
            'request': efile.request,
            'suggestion': efile.suggestion,
            'communications': communications,
            'attachments': attachments,
        }

    @http.route('/eoffice', type='http', auth='public', website=True,
                csrf=False)
    def show_identification_data(self, **kwargs):
        context = {}
        user_info = self.get_user_info(kwargs)
        if not user_info:
            template = 'eom_authdnie.identification_error'
        else:
            identif_token = user_info['identif_token']
            identif_header = user_info['identif_header']
            digitalregister = user_info['digitalregister']
            firstname = user_info['firstname']
            lastname = user_info['lastname']
            authority = user_info['authority']
            dni = user_info['dni']
            should_create_access = not kwargs.get('same_access', False)
            access = None
            if (should_create_access):
                model_eom_authdnie = request.env['eom.digitalregister'].sudo()
                access = model_eom_authdnie.create_access(
                    dni, firstname, lastname, authority)
            else:
                if (len(digitalregister.digitalregisteraccess_ids) > 0):
                    # Is ordered by event_time, so 0 must be the last one
                    access = digitalregister.digitalregisteraccess_ids[0]
            template = 'eom_authdnie.identification_data_page'
            context = {
                'identif_token': identif_token,
                'identif_header': identif_header,
                'digitalregister': digitalregister,
                'access': access,
            }
        return request.render(template, context)

    @http.route('/efiles', type='http', auth='public', website=True,
                csrf=False)
    def get_electronic_files(self, **kwargs):
        context = {}
        user_info = self.get_user_info(kwargs)
        if not user_info:
            template = 'eom_authdnie.identification_error'
        else:
            identif_token = user_info['identif_token']
            identif_header = user_info['identif_header']
            digitalregister = user_info['digitalregister']
            efiles = []
            if digitalregister:
                efiles_model = request.env['eom.electronicfile'].sudo()
                efiles = efiles_model.search([
                    ('digitalregister_id', '=', digitalregister.id),
                ]).mapped(
                    lambda x: self.format_efile(x, digitalregister))
            template = 'eom_eoffice.electronic_files_page'
            context = {
                'identif_token': identif_token,
                'identif_header': identif_header,
                'digitalregister': digitalregister,
                'efiles': efiles,
            }
        return request.render(template, context)

    @http.route('/efile', type='http', auth='public', website=True,
                csrf=False)
    def get_efile_data(self, **kwargs):
        context = {}
        user_info = self.get_user_info(kwargs)
        if not user_info:
            template = 'eom_authdnie.identification_error'
        else:
            identif_token = user_info['identif_token']
            identif_header = user_info['identif_header']
            digitalregister = user_info['digitalregister']
            efile = False
            if digitalregister:
                efile_id = kwargs.get('efile_id', False)
                efile_record = request.env[
                    'eom.electronicfile'].sudo().search([
                        ('digitalregister_id', '=', digitalregister.id),
                        ('id', '=', efile_id),
                    ], limit=1)
                if efile_record:
                    efile = self.format_efile(efile_record, digitalregister)
            template = 'eom_eoffice.electronic_file_page'
            context = {
                'identif_token': identif_token,
                'identif_header': identif_header,
                'digitalregister': digitalregister,
                'efile': efile,
            }
        return request.render(template, context)

    @http.route('/getdocument', type='http', auth='public', website=True,
                csrf=False)
    def get_document_from_csv(self, **kwargs):
        context = {}
        user_info = self.get_user_info(kwargs)
        if not user_info:
            template = 'eom_authdnie.identification_error'
        else:
            identif_token = user_info['identif_token']
            identif_header = user_info['identif_header']
            digitalregister = user_info['digitalregister']
            template = 'eom_eoffice.csv_code_form'
            context = {
                'identif_token': identif_token,
                'identif_header': identif_header,
                'digitalregister': digitalregister,
            }
        return request.render(template, context)

    @http.route('/document', type='http', auth='public', website=True,
                csrf=False)
    def search_document(self, **kwargs):
        context = {}
        user_info = self.get_user_info(kwargs)
        response = request.render('eom_authdnie.identification_error', {})
        if not user_info:
            template = 'eom_authdnie.identification_error'
        else:
            identif_token = user_info['identif_token']
            identif_header = user_info['identif_header']
            digitalregister = user_info['digitalregister']
            if digitalregister:
                csv_code = kwargs.get('csvcode', False)
                communication = request.env[
                    'eom.electronicfile.communication'].sudo().search([
                        ('electronicfile_id.digitalregister_id', '=',
                         digitalregister.id),
                        ('csv_code', '=', csv_code),
                    ], limit=1)
                if communication:
                    content = base64.b64decode(communication.document)
                    pdf_httpheaders = [
                        ('Content-Type', 'application/pdf'),
                        ('Content-Length', len(content)),
                        ('Content-Disposition',
                         'attachment; filename="%s.pdf"' %
                         communication.document_name)]
                    response = request.make_response(
                        content, headers=pdf_httpheaders)
                else:
                    template = 'eom_eoffice.csv_code_form'
                    context = {
                        'identif_token': identif_token,
                        'identif_header': identif_header,
                        'digitalregister': digitalregister,
                        'error_message': _('CSV not found'),
                    }
            else:
                template = 'eom_eoffice.csv_code_form'
                context = {
                    'identif_token': identif_token,
                    'identif_header': identif_header,
                    'digitalregister': digitalregister,
                    'error_message': _('Digitalregister not found'),
                }
            if context:
                response = request.render(template, context)
        return response

    @http.route('/setaddress', type='http', auth='public', website=True,
                csrf=False)
    def set_notification_address(self, **kwargs):
        context = {}
        user_info = self.get_user_info(kwargs)
        if not user_info:
            template = 'eom_authdnie.identification_error'
        else:
            identif_token = user_info['identif_token']
            identif_header = user_info['identif_header']
            digitalregister = user_info['digitalregister']
            template = 'eom_eoffice.notification_address_form'
            context = {
                'identif_token': identif_token,
                'identif_header': identif_header,
                'digitalregister': digitalregister,
            }
        return request.render(template, context)

    @http.route('/confirmaddress', type='http', auth='public', website=True,
                csrf=False)
    def confirm_notification_address(self, **kwargs):
        context = {}
        user_info = self.get_user_info(kwargs)
        template = 'eom_authdnie.identification_error'
        if user_info:
            identif_token = user_info['identif_token']
            identif_header = user_info['identif_header']
            digitalregister = user_info['digitalregister']
            if digitalregister:
                postal_notification = kwargs.get('postal_notification', False)
                notification_email = kwargs.get('notification_email', '')
                notification_phone = kwargs.get('notification_phone', '')
                notification_mobile = kwargs.get('notification_mobile', '')
                vals = {
                    'postal_notification': postal_notification == 'True',
                    'notification_email': notification_email,
                    'notification_phone': notification_phone,
                    'notification_mobile': notification_mobile,
                }
                if postal_notification == 'True':
                    notification_address = kwargs.get(
                        'notification_address', False)
                    vals['notification_address'] = notification_address
                digitalregister.sudo().write(vals)
                template = 'eom_eoffice.confirm_notification_address'
                context = {
                    'identif_token': identif_token,
                    'identif_header': identif_header,
                    'digitalregister': digitalregister,
                }
        return request.render(template, context)

    @http.route('/genericinstance', type='http', auth='public', website=True,
                csrf=False)
    def create_generic_instance(self, **kwargs):
        context = {}
        user_info = self.get_user_info(kwargs)
        if not user_info:
            template = 'eom_authdnie.identification_error'
        else:
            identif_token = user_info['identif_token']
            identif_header = user_info['identif_header']
            digitalregister = user_info['digitalregister']
            template = 'eom_eoffice.generic_instance_form'
            context = {
                'identif_token': identif_token,
                'identif_header': identif_header,
                'digitalregister': digitalregister,
            }
        return request.render(template, context)

    @http.route('/suggestion', type='http', auth='public', website=True,
                csrf=False)
    def create_suggestion(self, **kwargs):
        context = {}
        user_info = self.get_user_info(kwargs)
        if not user_info:
            template = 'eom_authdnie.identification_error'
        else:
            identif_token = user_info['identif_token']
            identif_header = user_info['identif_header']
            digitalregister = user_info['digitalregister']
            template = 'eom_eoffice.suggestion_form'
            context = {
                'identif_token': identif_token,
                'identif_header': identif_header,
                'digitalregister': digitalregister,
            }
        return request.render(template, context)

    @http.route('/confirmation', type='http', auth='public', website=True,
                csrf=False)
    def confirm_procedure(self, **kwargs):
        context = {}
        user_info = self.get_user_info(kwargs)
        template = 'eom_authdnie.identification_error'
        if user_info:
            identif_token = user_info['identif_token']
            identif_header = user_info['identif_header']
            digitalregister = user_info['digitalregister']
            electronicfile_code = ''
            if digitalregister:
                electronicfile_type = kwargs.get('electronicfile_type', False)
                if electronicfile_type:
                    vals = {
                        'digitalregister_id': digitalregister.id,
                        'type': electronicfile_type,
                    }
                    if electronicfile_type == '01_generic_instance':
                        vals['exposition'] = kwargs.get('exposition', False)
                        vals['request'] = kwargs.get('request', False)
                    elif electronicfile_type == '02_suggestion':
                        vals['suggestion'] = kwargs.get('suggestion', False)
                    model_electronicfile = request.env[
                        'eom.electronicfile'].sudo()
                    uploaded_files = request.httprequest.files.getlist(
                        'attachments')
                    # Check upload size
                    if uploaded_files:
                        max_size_reached, max_size_attachments, \
                            total_attachments_size = \
                            self.check_upload_files_size(uploaded_files)
                        if max_size_reached:
                            template = 'eom_eoffice.error_max_size_attachments'
                            context = {
                                'identif_token': identif_token,
                                'identif_header': identif_header,
                                'digitalregister': digitalregister,
                                'max_size_attachments': max_size_attachments,
                                'total_attachments_size':
                                    total_attachments_size}
                            return request.render(template, context)
                    # Create electronicfile
                    electronicfile = model_electronicfile.create(vals)
                    electronicfile_code = electronicfile.name
                    if uploaded_files:
                        max_size_attachments = \
                            request.env['ir.default'].sudo().get(
                                'res.config.settings',
                                'max_size_attachments')
                        total_attachments_size_bytes = 0.0
                        for file in uploaded_files:
                            file.stream.seek(0, 2)
                            total_attachments_size_bytes += file.stream.tell()
                            file.stream.seek(0)
                        total_attachments_size = \
                            total_attachments_size_bytes / (1024 * 1024)
                        if total_attachments_size > max_size_attachments:
                            template = 'eom_eoffice.error_max_size_attachments'
                            context = {
                                'identif_token': identif_token,
                                'identif_header': identif_header,
                                'digitalregister': digitalregister,
                                'max_size_attachments': max_size_attachments,
                                'total_attachments_size':
                                    total_attachments_size,
                            }
                            return request.render(template, context)
                        for uploaded_file in uploaded_files:
                            name = uploaded_file.filename
                            datas = base64.b64encode(uploaded_file.read())
                            if name and datas:
                                request.env['ir.attachment'].sudo().create({
                                    'name': name,
                                    'datas': datas,
                                    'name': name,
                                    'type': 'binary',
                                    'res_name': electronicfile.name,
                                    'res_model': 'eom.electronicfile',
                                    'res_id': electronicfile.id,
                                })
                    model_communication = request.env[
                        'eom.electronicfile.communication'].sudo()
                    communication_date = self.transform_time_to_locale(
                        fields.Datetime.now(), digitalregister)
                    communication_text = _(
                        'Electronic file with code %s '
                        'has been created correctly on %s') % (
                            electronicfile.name, communication_date)
                    vals = {
                        'state': '01_draft',
                        'electronicfile_id': electronicfile.id,
                        'issue': _('Procedure confirmed'),
                        'communication_text': communication_text,
                        'validation_time': fields.Datetime.now(),
                        'reading_time': fields.Datetime.now(),
                        'is_notification': True,
                    }
                    communication = model_communication.create(vals)
                    communication.action_go_to_state_02_validated()
                    communication.action_mark_as_readed()
                    template = 'eom_eoffice.confirmation_and_home'
                    context = {
                        'identif_token': identif_token,
                        'identif_header': identif_header,
                        'digitalregister': digitalregister,
                        'electronicfile_code': electronicfile_code,
                        'csv_code': communication.csv_code,
                    }
        return request.render(template, context)

    @http.route('/efile_attachment', type='http', auth='public',
                website=True, csrf=False)
    def download_attachment_efile(self, **kwargs):
        user_info = self.get_user_info(kwargs)
        response = request.render('eom_authdnie.identification_error', {})
        if user_info:
            digitalregister = user_info['digitalregister']
            if digitalregister:
                efile_id = kwargs.get('efile_id', False)
                attachment_id = kwargs.get('attachment_id', False)
                efile = request.env['eom.electronicfile'].sudo().search([
                    ('id', '=', int(efile_id)),
                    ('digitalregister_id', '=', digitalregister.id),
                ], limit=1)
                if efile:
                    attachment = request.env['ir.attachment'].sudo().search([
                        ('id', '=', int(attachment_id)),
                        ('res_model', '=', 'eom.electronicfile'),
                        ('res_id', '=', efile.id),
                    ], limit=1)
                    file_content = StringIO(base64.b64decode(
                        attachment.datas))
                    response = http.send_file(
                        file_content,
                        filename=attachment.name or attachment.name,
                        as_attachment=True)
        return response

    @http.route('/communication_attachment', type='http', auth='public',
                website=True, csrf=False)
    def download_attachment_communication(self, **kwargs):
        user_info = self.get_user_info(kwargs)
        request.render('eom_authdnie.identification_error', {})
        if user_info:
            digitalregister = user_info['digitalregister']
            if digitalregister:
                communication_id = kwargs.get('communication_id', False)
                attachment_id = kwargs.get('attachment_id', False)
                communication = request.env[
                    'eom.electronicfile.communication'].sudo().search([
                        ('id', '=', int(communication_id)),
                        ('electronicfile_id.digitalregister_id', '=',
                         digitalregister.id),
                    ], limit=1)
                if communication:
                    attachment = request.env['ir.attachment'].sudo().search([
                        ('id', '=', int(attachment_id)),
                        ('res_model', '=',
                         'eom.electronicfile.communication'),
                        ('res_id', '=', communication.id),
                    ], limit=1)
                    file_content = StringIO(
                        base64.b64decode(attachment.datas))
                    response = http.send_file(
                        file_content,
                        filename=(attachment.name or attachment.name).
                        encode('utf-8'),
                        as_attachment=True)
        return response

    @http.route('/communication', type='http', auth='public', website=True,
                csrf=False)
    def handle_communication(self, **kwargs):
        context = {}
        user_info = self.get_user_info(kwargs)
        template = 'eom_authdnie.identification_error'
        response = request.render(template, context)
        if user_info:
            identif_token = user_info['identif_token']
            identif_header = user_info['identif_header']
            digitalregister = user_info['digitalregister']
            button_action = kwargs.get('action', False)
            if digitalregister:
                communication_id = kwargs.get('communication_id', False)
                communication_record = request.env[
                    'eom.electronicfile.communication'].sudo().search([
                        ('electronicfile_id.digitalregister_id', '=',
                         digitalregister.id),
                        ('id', '=', communication_id),
                    ], limit=1)
                if communication_record:
                    communication_obj = communication_record
                    efile_obj = communication_obj.electronicfile_id
                    if (button_action == 'read' and
                            communication_obj.is_notification and
                            communication_obj.state == '02_validated'):
                        communication_obj.action_mark_as_readed()
                    elif (button_action == 'reject' and
                          communication_obj.is_notification and
                          communication_obj.state == '02_validated'):
                        communication_obj.action_mark_as_rejected()
                    communication = self.format_communication(
                        communication_obj, digitalregister)
                    efile = self.format_efile(efile_obj, digitalregister)
                    if button_action == 'view':
                        template = \
                            'eom_eoffice.electronic_file_communication_page'
                        context = {
                            'identif_token': identif_token,
                            'identif_header': identif_header,
                            'digitalregister': digitalregister,
                            'communication': communication,
                        }
                        response = request.render(template, context)
                    elif button_action == 'read':
                        file_content = StringIO(base64.b64decode(
                            communication_obj.document))
                        response = http.send_file(
                            file_content,
                            filename=communication_obj.document_name,
                            as_attachment=True)
                    else:
                        template = 'eom_eoffice.electronic_file_page'
                        context = {
                            'identif_token': identif_token,
                            'identif_header': identif_header,
                            'digitalregister': digitalregister,
                            'efile': efile,
                        }
                        response = request.render(template, context)
        return response

    @http.route('/addcommunication', type='http', auth='public',
                website=True, csrf=False)
    def create_communication(self, **kwargs):
        context = {}
        user_info = self.get_user_info(kwargs)
        template = 'eom_authdnie.identification_error'
        if user_info:
            identif_token = user_info['identif_token']
            identif_header = user_info['identif_header']
            digitalregister = user_info['digitalregister']
            efile = False
            if digitalregister:
                efile_id = kwargs.get('efile_id', False)
                issue = kwargs.get('issue', False)
                communication_text = kwargs.get('communication_text', False)
                efile_record = request.env['eom.electronicfile'].sudo().\
                    search([
                        ('digitalregister_id', '=', digitalregister.id),
                        ('id', '=', efile_id),
                    ], limit=1)
                if efile_record:
                    model_communication = request.env[
                        'eom.electronicfile.communication'].sudo()
                    vals = {
                        'state': '02_validated',
                        'electronicfile_id': efile_record.id,
                        'issue': issue,
                        'communication_text': communication_text,
                        'validation_time': fields.Datetime.now(),
                        'is_notification': False,
                    }
                    uploaded_files = request.httprequest.files.getlist(
                        'attachments')
                    # Check upload size
                    if uploaded_files:
                        max_size_reached, max_size_attachments, \
                            total_attachments_size = \
                            self.check_upload_files_size(uploaded_files)
                        if max_size_reached:
                            template = 'eom_eoffice.error_max_size_attachments'
                            context = {
                                'identif_token': identif_token,
                                'identif_header': identif_header,
                                'digitalregister': digitalregister,
                                'max_size_attachments': max_size_attachments,
                                'total_attachments_size':
                                    total_attachments_size}
                            return request.render(template, context)
                    # Create communication
                    communication = model_communication.create(vals)
                    if uploaded_files:
                        for uploaded_file in uploaded_files:
                            name = uploaded_file.filename
                            datas = base64.b64encode(uploaded_file.read())
                            if name and datas:
                                request.env['ir.attachment'].sudo().create({
                                    'name': name,
                                    'datas': datas,
                                    'name': name,
                                    'type': 'binary',
                                    'res_name': communication.name,
                                    'res_model':
                                        'eom.electronicfile.communication',
                                    'res_id': communication.id,
                                })
                    efile = self.format_efile(efile_record, digitalregister)
                    template = 'eom_eoffice.electronic_file_page'
                    context = {
                        'identif_token': identif_token,
                        'identif_header': identif_header,
                        'digitalregister': digitalregister,
                        'efile': efile,
                    }
        return request.render(template, context)

    def check_upload_files_size(self, uploaded_files):
        max_size_reached = False
        max_size_attachments = request.env['ir.default'].sudo().get(
            'res.config.settings', 'max_size_attachments') or 0.0
        total_attachments_size_bytes = 0.0
        for file in uploaded_files:
            file.stream.seek(0, 2)
            total_attachments_size_bytes += file.stream.tell()
            file.stream.seek(0)
        total_attachments_size = \
            total_attachments_size_bytes / (1024 * 1024)
        if total_attachments_size > max_size_attachments:
            max_size_reached = True
        return max_size_reached, max_size_attachments, total_attachments_size
