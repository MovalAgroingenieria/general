# -*- coding: utf-8 -*-
# Copyright 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
import string
import random
import locale
from datetime import datetime
from dateutil.relativedelta import relativedelta
from lxml import etree
from Crypto import Random
from Crypto.Cipher import AES
from odoo import models, fields, api, modules, exceptions, _


class CimComplaint(models.Model):
    _name = 'cim.complaint'
    _description = 'Complaint'
    _inherit = 'mail.thread'
    _order = 'name'

    SIZE_SMALL = 25
    SIZE_MEDIUM = 50
    SIZE_MEDIUM_EXTRA = 75
    SIZE_NORMAL = 100
    SIZE_BIG = 255
    MAX_DOCUMENTS = 6

    _size_tracking_code = 8
    _cipher_key = 'z%C*F-JaNdRgUkXp'

    def _default_tracking_code(self):
        characters = string.ascii_uppercase + string.digits
        # String to cipher
        tracking_code_ok = False
        tracking_code = ''
        while not tracking_code_ok:
            tracking_code = ''.join(random.choice(characters)
                                    for _ in range(self._size_tracking_code))
            repeated_complaints = self.search(
                [('tracking_code', '=', tracking_code)])
            if not repeated_complaints:
                tracking_code_ok = True
        # Encrypt
        resp = self.encrypt_data(tracking_code, self._cipher_key)
        return resp

    def _default_setted_sequence(self):
        resp = False
        config = self.env['ir.config_parameter'].sudo()
        sequence_complaint_code_id = config.get_param(
            'cim_complaints_channel.sequence_complaint_code_id', False)
        if sequence_complaint_code_id:
            resp = True
        return resp

    @api.model
    def _lang_get(self):
        return self.env['res.lang'].get_installed()

    name = fields.Char(
        string='Code',
        size=SIZE_SMALL,
        index=True,)

    issue = fields.Char(
        string='Issue',
        size=SIZE_MEDIUM_EXTRA,
        required=True,
        index=True,)

    description = fields.Text(
        string='Facts denounced',
        required=True,
        index=True,)

    tracking_code = fields.Char(
        string='Tracking Code',
        size=SIZE_BIG,
        default=_default_tracking_code,
        readonly=True,)

    complaint_type_id = fields.Many2one(
        string='Complaint Type',
        comodel_name='cim.complaint.type',
        index=True,
        ondelete='restrict',)

    defendant_name = fields.Char(
        string='Defendant Name',
        size=SIZE_NORMAL,
        index=True,)

    witness_name = fields.Text(
        string='Witnesses',)

    is_complainant_involved = fields.Boolean(
        string='Complainant involved',
        default=False,
        required=True,)

    link_type_id = fields.Many2one(
        string='Link Type',
        comodel_name='cim.link.type',
        index=True,
        ondelete='restrict',)

    complaint_frequency = fields.Selection(
        string="Complaint Frequency",
        selection=[
            ('01_not_remembered', 'Not remembered'),
            ('02_specific_day', 'A specific day'),
            ('03_continuously', 'Continuously'),
        ],
        default='01_not_remembered',
        required=True,
        index=True,)

    complaint_time = fields.Datetime(
        string='Complaint Time',)

    complaint_date = fields.Date(
        string='Complaint Date',
        store=True,
        index=True,
        compute='_compute_complaint_date',)

    creation_date = fields.Date(
        string='Creation Date',
        required=True,
        default=lambda self: fields.datetime.now(),)

    complainant_email = fields.Char(
        string='Complainant E-mail',)

    complainant_name = fields.Char(
        string='Complainant Name',)

    complainant_vat = fields.Char(
        string='Complainant VAT',)

    complainant_phone = fields.Char(
        string='Complainant Phone',)

    is_anonymous = fields.Boolean(
        string='Anonymous Complaint',
        default=True,
        store=True,
        compute='_compute_is_anonymous')

    measures_taken = fields.Text(
        string='Measures taken',
        index=True,)

    resolution_text = fields.Text(
        string='Resolution Text',)

    user_in_group_cim_settings = fields.Boolean(
        string='Is a complaints administrator?',
        compute='_compute_user_in_group_cim_settings',)

    is_delegated = fields.Boolean(
        string='Delegated Complaint',
        default=False,
        readonly=True,)

    notes = fields.Html(
        string='Notes',)

    state = fields.Selection(
        string="State",
        selection=[
            ('01_received',
             'Received'),
            ('02_admitted',
             'Admitted'),
            ('03_in_progress',
             'In progress'),
            ('04_ready',
             'Ready'),
            ('05_resolved',
             'Resolved'),
        ],
        default='01_received',
        required=True,
        index=True,
        tracking=True,)

    investigating_user_id = fields.Many2one(
        string='Instructor',
        comodel_name='res.users',
        tracking=True,)

    communication_ids = fields.One2many(
        string='Communications',
        comodel_name='cim.complaint.communication',
        inverse_name='complaint_id',)

    number_of_communications = fields.Integer(
        string='Number of communications',
        compute='_compute_number_of_communications',)

    is_rejected = fields.Boolean(
        string='Rejected complaint',
        default=False,
        readonly=True,
        tracking=True,)

    rejection_cause = fields.Text(
        string='Cause of the rejection',)

    is_extended = fields.Boolean(
        string='Extended process',
        default=False,
        readonly=True,
        tracking=True,)

    param_acknowledgement_period = fields.Integer(
        string='Acknowledgement period (number of days)',
        compute='_compute_param_acknowledgement_period',)

    param_notice_period = fields.Integer(
        string='Notice Period (number of days)',
        compute='_compute_param_notice_period',)

    param_deadline = fields.Integer(
        string='Deadline (number of months)',
        compute='_compute_param_deadline',)

    param_deadline_extended = fields.Integer(
        string='Extended Deadline (number of months)',
        compute='_compute_param_deadline_extended',)

    param_email_for_notice = fields.Char(
        string='E-mail for notice',
        compute='_compute_param_email_for_notice',)

    deadline_date = fields.Date(
        string='Deadline Date',
        compute='_compute_deadline_date',)

    deadline_state = fields.Selection(
        string='Deadline Status',
        selection=[
            ('01_on_time',
             'Instruction on time'),
            ('02_upcoming_expiration',
             'Instruction deadline soon to expire'),
            ('03_expirated',
             'Instruction period expirated'),
            ('04_extended',
             'Extended instruction on time'),
            ('05_extended_upcoming_expiration',
             'Extended instruction deadline soon to expire'),
            ('06_extended_expirated',
             'Extended instruction period expirated'),
            ('07_finished',
             'Instruction finished'),
            ('99_rejected',
             'Instruction rejected'),
        ],
        default='01_on_time',
        compute='_compute_deadline_state',)

    is_acknowledgement_expired = fields.Boolean(
        string='Expired acknowledgement',
        default=False,
        compute='_compute_is_acknowledgement_expired',
        search='_search_is_acknowledgement_expired',)

    infringement_level = fields.Selection(
        string="Infringement Level",
        selection=[
            ('01_mild',
             'Mild'),
            ('02_serious',
             'Serious'),
            ('03_very_serious',
             'Very Serious'),
        ],
        default='01_mild',
        required=True,
        index=True,)

    resolution_date = fields.Date(
        string='Resolution Date',
        index=True,)

    expected_resolution_date = fields.Date(
        string='Expected Resolution Date',
        store=True,
        index=True,
        compute='_compute_expected_resolution_date',)

    is_juditial_action = fields.Boolean(
        string='Juditial Action',
        default=False,)

    setted_sequence = fields.Boolean(
        string='Setted Sequence (y/n)',
        default=_default_setted_sequence,
        compute='_compute_setted_sequence',)

    summary_info = fields.Char(
        string='Summary',
        compute='_compute_summary_info',)

    document_01 = fields.Binary(
        string='Attachment 1',
        attachment=True,)

    document_01_name = fields.Char(
        string='Name of the attachment 1',)

    document_02 = fields.Binary(
        string='Attachment 2',
        attachment=True,)

    document_02_name = fields.Char(
        string='Name of the attachment 2',)

    document_03 = fields.Binary(
        string='Attachment 3',
        attachment=True,)

    document_03_name = fields.Char(
        string='Name of the attachment 3',)

    document_04 = fields.Binary(
        string='Attachment 4',
        attachment=True,)

    document_04_name = fields.Char(
        string='Name of the attachment 4',)

    document_05 = fields.Binary(
        string='Attachment 5',
        attachment=True,)

    document_05_name = fields.Char(
        string='Name of the attachment 5',)

    document_06 = fields.Binary(
        string='Attachment 6',
        attachment=True,)

    document_06_name = fields.Char(
        string='Name of the attachment 6',)

    number_of_attachments = fields.Integer(
        string='Number of attachments',
        compute='_compute_number_of_attachments',)

    icon_warning = fields.Binary(
        string='Icon for warnings',
        compute='_compute_icon_warning')

    decrypted_tracking_code = fields.Char(
        string='Decrypted tracking code',
        compute='_compute_decrypted_tracking_code',)

    decrypted_complainant_name = fields.Char(
        string='Decrypted complainant name',
        compute='_compute_decrypted_complainant_name',)

    decrypted_complainant_email = fields.Char(
        string='Decrypted complainant e-mail',
        compute='_compute_decrypted_complainant_email',)

    decrypted_complainant_vat = fields.Char(
        string='Decrypted complainant VAT',
        compute='_compute_decrypted_complainant_vat',)

    decrypted_complainant_phone = fields.Char(
        string='Decrypted complainant phone',
        compute='_compute_decrypted_complainant_phone',)

    decrypted_witness_name = fields.Text(
        string='Decrypted witness name',
        compute='_compute_decrypted_witness_name',)

    decrypted_complainant_data = fields.Text(
        string='Decrypted Complainant Data',
        compute='_compute_decrypted_complainant_data',)

    complaint_lang = fields.Selection(
        selection=_lang_get,
        string="Language",)

    automatic_email_state = fields.Boolean(
        string='E-mail to complainant after complaint change state (y/n)',
        compute='_compute_automatic_email_state',)

    @api.depends('complaint_time')
    def _compute_complaint_date(self):
        for record in self:
            complaint_date = None
            if record.complaint_time:
                complaint_date = record.complaint_time
            record.complaint_date = complaint_date

    @api.depends('complainant_name', 'complainant_vat', 'complainant_phone')
    def _compute_is_anonymous(self):
        for record in self:
            is_anonymous = True
            if (record.complainant_name or record.complainant_vat or
                    record.complainant_phone):
                is_anonymous = False
            record.is_anonymous = is_anonymous

    def _compute_user_in_group_cim_settings(self):
        user_in_group_cim_settings = \
            self.env.user.has_group(
                'cim_complaints_channel.group_cim_settings')
        for record in self:
            record.user_in_group_cim_settings = user_in_group_cim_settings

    def _compute_number_of_communications(self):
        for record in self:
            number_of_communications = 0
            if record.communication_ids:
                number_of_communications = len(record.communication_ids)
            record.number_of_communications = number_of_communications

    def _compute_param_acknowledgement_period(self):
        config = self.env['ir.config_parameter'].sudo()
        param_acknowledgement_period = config.get_param(
            'cim_complaints_channel.acknowledgement_period', False)
        if not param_acknowledgement_period:
            param_acknowledgement_period = 0
        for record in self:
            record.param_acknowledgement_period = param_acknowledgement_period

    def _compute_param_notice_period(self):
        config = self.env['ir.config_parameter'].sudo()
        param_notice_period = config.get_param(
            'cim_complaints_channel.notice_period', False)
        if not param_notice_period:
            param_notice_period = 10
        for record in self:
            record.param_notice_period = param_notice_period

    def _compute_param_deadline(self):
        config = self.env['ir.config_parameter'].sudo()
        param_deadline = config.get_param(
            'cim_complaints_channel.deadline', False)
        if not param_deadline:
            param_deadline = 1
        for record in self:
            record.param_deadline = param_deadline

    def _compute_param_deadline_extended(self):
        config = self.env['ir.config_parameter'].sudo()
        param_deadline_extended = config.get_param(
            'cim_complaints_channel.deadline_extended', False)
        if not param_deadline_extended:
            param_deadline_extended = 1
        for record in self:
            record.param_deadline_extended = param_deadline_extended

    def _compute_param_email_for_notice(self):
        config = self.env['ir.config_parameter'].sudo()
        param_email_for_notice = config.get_param(
            'cim_complaints_channel.email_for_notice', False)
        if not param_email_for_notice:
            param_email_for_notice = ''
        param_email_for_notice = param_email_for_notice.strip()
        for record in self:
            record.param_email_for_notice = param_email_for_notice

    def _compute_deadline_date(self):
        for record in self:
            instruction_months = record.param_deadline
            if record.is_extended:
                instruction_months = record.param_deadline_extended
            deadline_date = (record.creation_date +
                             relativedelta(months=instruction_months, days=-1)).strftime('%Y-%m-%d')
            record.deadline_date = deadline_date

    def _compute_deadline_state(self):
        for record in self:
            deadline_state = '07_finished'
            if record.is_rejected:
                deadline_state = '99_rejected'
            elif record.state != '05_resolved':
                current_date = datetime.today().strftime('%Y-%m-%d')
                months_deadline = record.param_deadline
                if record.is_extended:
                    months_deadline = record.param_deadline_extended
                deadline_date = (record.creation_date + relativedelta(
                    months=months_deadline, days=-1)).strftime('%Y-%m-%d')
                if current_date <= deadline_date:
                    deadline_state = '01_on_time'
                    if record.is_extended:
                        deadline_state = '04_extended'
                    deadline_notice = (datetime.strptime(
                        deadline_date, '%Y-%m-%d') + relativedelta(
                        days=-record.param_notice_period + 1)).strftime(
                            '%Y-%m-%d')
                    if current_date >= deadline_notice:
                        deadline_state = '02_upcoming_expiration'
                        if record.is_extended:
                            deadline_state = '05_extended_upcoming_expiration'
                else:
                    deadline_state = '03_expirated'
                    if record.is_extended:
                        deadline_state = '06_extended_expirated'
            record.deadline_state = deadline_state

    def _compute_is_acknowledgement_expired(self):
        for record in self:
            is_acknowledgement_expired = False
            if not record.is_rejected and record.state == '01_received':
                deadline_acknowledgement = (record.creation_date + relativedelta(
                    days=record.param_acknowledgement_period - 1)).strftime('%Y-%m-%d')
                current_date = datetime.today().strftime('%Y-%m-%d')
                if current_date > deadline_acknowledgement:
                    is_acknowledgement_expired = True
            record.is_acknowledgement_expired = is_acknowledgement_expired

    def _search_is_acknowledgement_expired(self, operator, value):
        complaint_ids = []
        operator_of_filter = 'in'
        is_acknowledgement_expired = ((operator == '=' and value) or
                                      (operator == '!=' and not value))
        if not is_acknowledgement_expired:
            operator_of_filter = 'not in'
        acknowledgement_period = 0
        config = self.env['ir.config_parameter'].sudo()
        param_acknowledgement_period = config.get_param(
            'cim_complaints_channel.acknowledgement_period', False)
        if param_acknowledgement_period:
            acknowledgement_period = int(param_acknowledgement_period)
        where_clause = 'is_rejected = false and state = \'01_received\''
        if acknowledgement_period >= 0:
            where_clause = where_clause + ' and current_date - ' + \
                           str(acknowledgement_period) + \
                           ' >= creation_date'
        sql_statement = 'select id from cim_complaint where ' + where_clause
        self.env.cr.execute(sql_statement)
        sql_resp = self.env.cr.fetchall()
        if sql_resp:
            for item in sql_resp:
                complaint_ids.append(item[0])
        return [('id', operator_of_filter, complaint_ids)]

    @api.depends('creation_date', 'resolution_date')
    def _compute_expected_resolution_date(self):
        for record in self:
            expected_resolution_date = record.deadline_date
            if record.resolution_date:
                expected_resolution_date = record.resolution_date
            record.expected_resolution_date = expected_resolution_date

    def _compute_setted_sequence(self):
        config = self.env['ir.config_parameter'].sudo()
        sequence_complaint_code_id = config.get_param(
            'cim_complaints_channel.sequence_complaint_code_id', False)
        for record in self:
            setted_sequence = False
            if sequence_complaint_code_id:
                setted_sequence = True
            record.setted_sequence = setted_sequence

    def _compute_summary_info(self):
        for record in self:
            preffix_info = record.name + '. ' + record.complaint_type_id.name
            suffix_info = _('COMPLAINT REJECTED') + '.'
            if not record.is_rejected:
                suffix_info = self._additional_summary_info(record)
            record.summary_info = preffix_info + '. ' + suffix_info

    @api.model
    def _additional_summary_info(self, complaint):
        infringement_level = _('Mild')
        if complaint.infringement_level == '02_serious':
            infringement_level = _('SERIOUS')
        elif complaint.infringement_level == '03_very_serious':
            infringement_level = _('VERY SERIOUS')
        state = _('Received')
        if complaint.state == '02_admitted':
            state = _('Admitted')
        elif complaint.state == '03_in_progress':
            state = _('In progress')
        elif complaint.state == '04_ready':
            state = _('Ready')
        elif complaint.state == '05_resolved':
            state = _('Resolved')
        issue = complaint.issue
        if issue[-1] != '.':
            issue = issue + '.'
        resp = _('Severity:') + ' ' + infringement_level + '. ' + \
            _('State:') + ' ' + state + '. ' + \
            _('Issue:') + ' ' + issue
        return resp

    def _compute_number_of_attachments(self):
        for record in self:
            number_of_attachments = self.MAX_DOCUMENTS
            if not record.document_06_name:
                number_of_attachments = number_of_attachments - 1
                if not record.document_05_name:
                    number_of_attachments = number_of_attachments - 1
                    if not record.document_04_name:
                        number_of_attachments = number_of_attachments - 1
                        if not record.document_03_name:
                            number_of_attachments = number_of_attachments - 1
                            if not record.document_02_name:
                                number_of_attachments = \
                                        number_of_attachments - 1
                                if not record.document_01_name:
                                    number_of_attachments = \
                                            number_of_attachments - 1
            record.number_of_attachments = number_of_attachments

    def _compute_icon_warning(self):
        image_path_is_acknowledgement_expired_no = \
            modules.module.get_resource_path('cim_complaints_channel',
                                             'static/img', 'icon_ontime.png')
        image_path_is_acknowledgement_expired_yes = \
            modules.module.get_resource_path(
                'cim_complaints_channel',
                'static/img', 'icon_expirated.png')
        image_path_is_rejected = \
            modules.module.get_resource_path('cim_complaints_channel',
                                             'static/img', 'icon_rejected.png')
        for record in self:
            icon_warning = None
            image_path = None
            if record.is_rejected:
                image_path = image_path_is_rejected
            elif record.state == '01_received':
                if record.is_acknowledgement_expired:
                    image_path = image_path_is_acknowledgement_expired_yes
                else:
                    image_path = image_path_is_acknowledgement_expired_no
            if image_path:
                image_file = open(image_path, 'rb')
                icon_warning = base64.b64encode(image_file.read())
            record.icon_warning = icon_warning

    def _compute_decrypted_tracking_code(self):
        for record in self:
            decrypted_tracking_code = ''
            if record.tracking_code:
                decrypted_tracking_code = self.decrypt_data(
                    record.tracking_code, self._cipher_key)
            record.decrypted_tracking_code = decrypted_tracking_code

    def _compute_decrypted_complainant_name(self):
        for record in self:
            decrypted_complainant_name = ''
            if record.complainant_name:
                decrypted_complainant_name = self.decrypt_data(
                    record.complainant_name, self._cipher_key)
            record.decrypted_complainant_name = decrypted_complainant_name

    def _compute_decrypted_complainant_email(self):
        for record in self:
            decrypted_complainant_email = ''
            if record.complainant_email:
                decrypted_complainant_email = self.decrypt_data(
                    record.complainant_email, self._cipher_key)
            record.decrypted_complainant_email = decrypted_complainant_email

    def _compute_decrypted_complainant_vat(self):
        for record in self:
            decrypted_complainant_vat = ''
            if record.complainant_vat:
                decrypted_complainant_vat = self.decrypt_data(
                    record.complainant_vat, self._cipher_key)
            record.decrypted_complainant_vat = decrypted_complainant_vat

    def _compute_decrypted_complainant_phone(self):
        for record in self:
            decrypted_complainant_phone = ''
            if record.complainant_phone:
                decrypted_complainant_phone = self.decrypt_data(
                    record.complainant_phone, self._cipher_key)
            record.decrypted_complainant_phone = decrypted_complainant_phone

    def _compute_decrypted_witness_name(self):
        for record in self:
            decrypted_witness_name = ''
            if record.witness_name:
                decrypted_witness_name = self.decrypt_data(
                    record.witness_name, self._cipher_key)
            record.decrypted_witness_name = decrypted_witness_name

    def _compute_decrypted_complainant_data(self):
        for record in self:
            decrypted_complainant_data = ''
            decrypted_complainant_name = record.decrypted_complainant_name
            decrypted_complainant_email = record.decrypted_complainant_email
            decrypted_complainant_vat = record.decrypted_complainant_vat
            decrypted_complainant_phone = record.decrypted_complainant_phone
            if decrypted_complainant_name:
                decrypted_complainant_data = decrypted_complainant_name + '\n'
            if decrypted_complainant_vat:
                decrypted_complainant_data = decrypted_complainant_data + \
                                             decrypted_complainant_vat + '\n'
            if decrypted_complainant_email:
                decrypted_complainant_data = decrypted_complainant_data + \
                                             decrypted_complainant_email + '\n'
            if decrypted_complainant_phone:
                decrypted_complainant_data = decrypted_complainant_data + \
                                             decrypted_complainant_phone + '\n'
            if decrypted_complainant_data:
                decrypted_complainant_data = decrypted_complainant_data[:-1]
            record.decrypted_complainant_data = decrypted_complainant_data

    def _compute_automatic_email_state(self):
        config = self.env['ir.config_parameter'].sudo()
        automatic_email_state = config.get_param(
            'cim_complaints_channel.automatic_email_state', False)
        for record in self:
            record.automatic_email_state = automatic_email_state

    @api.constrains('is_rejected', 'state')
    def _check_is_rejected(self):
        for record in self:
            if record.state != '01_received' and record.is_rejected:
                raise exceptions.ValidationError(
                    _('It is only possible to reject a complaint if its '
                      'state is \'Received\'.'))

    @api.constrains('investigating_user_id', 'state')
    def _check_investigating_user_id(self):
        for record in self:
            if ((not record.investigating_user_id) and
               (record.state in ('04_ready', '05_resolved'))):
                raise exceptions.ValidationError(
                    _('If the complaint is ready or resolved, then it is '
                      'mandatory to enter the instructor.'))

    @api.constrains('measures_taken', 'state')
    def _check_measures_taken(self):
        for record in self:
            if ((record.state in ('04_ready', '05_resolved'))
                    and ((not record.measures_taken) or
                         record.measures_taken == '')):
                raise exceptions.ValidationError(
                    _('If the complaint is ready or resolved, then it is '
                      'mandatory to enter the measures taken.'))

    @api.constrains('resolution_text', 'state')
    def _check_resolution_text(self):
        for record in self:
            if record.state == '05_resolved' and (not record.resolution_text):
                raise exceptions.ValidationError(
                    _('If the complaint is resolved, then it is mandatory '
                      'to enter the resolution text.'))

    def name_get(self):
        result = []
        for record in self:
            display_name = record.name + \
                           ' (' + record.complaint_type_id.name + ')'
            result.append((record.id, display_name))
        return result

    @api.model_create_multi
    def create(self, vals_list):
        config = self.env['ir.config_parameter'].sudo()
        sequence_complaint_code_id = config.get_param(
            'cim_complaints_channel.sequence_complaint_code_id', False)
        for vals in vals_list:
            if sequence_complaint_code_id:
                model_ir_sequence = self.env['ir.sequence'].sudo()
                sequence_complaint_code = \
                    model_ir_sequence.browse(int(sequence_complaint_code_id))
                if sequence_complaint_code:
                    new_code = model_ir_sequence.next_by_code(
                        sequence_complaint_code.code)
                    vals['name'] = new_code
            else:
                if 'name' in vals and vals['name']:
                    vals['name'] = vals['name'].strip()
            if ('name' not in vals) or (not vals['name']):
                raise exceptions.ValidationError(_('It is mandatory to enter a '
                                                   'code for the new complaint.'))
            vals = self._process_vals(vals, is_create=True)
        new_complaints = super(CimComplaint, self).create(vals_list)
        for new_complaint in new_complaints:
            if new_complaint.complainant_email:
                mail_template_tracking_code = None
                try:
                    mail_template_tracking_code = self.env.ref(
                        'cim_complaints_channel.'
                        'mail_template_tracking_code').sudo()
                except Exception:
                    mail_template_tracking_code = None
                if mail_template_tracking_code:
                    user_lang = 'en_US'
                    if new_complaint.complaint_lang:
                        user_lang = new_complaint.complaint_lang
                    mail_template_tracking_code.with_context(
                        lang=user_lang).send_mail(
                            new_complaint.id, force_send=True)
            new_complaint.create_initial_communication()
        return new_complaints

    def write(self, vals):
        vals = self._process_vals(vals)
        super().write(vals)
        return True

    @api.model
    def _process_vals(self, vals, is_create=False):
        if vals:
            if 'state' in vals and vals['state']:
                if vals['state'] == '05_resolved':
                    vals['resolution_date'] = \
                        datetime.now().strftime('%Y-%m-%d')
                else:
                    vals['resolution_date'] = None
            if ((is_create or len(self) == 1) and
                    ('document_01' in vals or 'document_02' in vals or
                     'document_03' in vals or 'document_04' in vals or
                     'document_05' in vals or 'document_06' in vals)):
                vals = self._compact_document_fields(vals, is_create)
            if (is_create and ('complaint_type_id' not in vals or
                               (not vals['complaint_type_id']))):
                vals['complaint_type_id'] = self.env.ref(
                    'cim_complaints_channel.cim_complaint_type_other').id
            if (is_create and ('link_type_id' not in vals or
                               (not vals['link_type_id']))):
                vals['link_type_id'] = self.env.ref(
                    'cim_complaints_channel.cim_link_type_other').id
            if (is_create and ('document_01_name' in vals) and
               ('document_01' not in vals)):
                vals.pop('document_01_name')
            if (is_create and ('document_02_name' in vals) and
               ('document_02' not in vals)):
                vals.pop('document_02_name')
            if (is_create and ('document_03_name' in vals) and
               ('document_03' not in vals)):
                vals.pop('document_03_name')
            if (is_create and ('document_04_name' in vals) and
               ('document_04' not in vals)):
                vals.pop('document_04_name')
            if (is_create and ('document_05_name' in vals) and
               ('document_05' not in vals)):
                vals.pop('document_05_name')
            if (is_create and ('document_06_name' in vals) and
               ('document_06' not in vals)):
                vals.pop('document_06_name')
            if 'complaint_frequency' in vals and vals['complaint_frequency']:
                if vals['complaint_frequency'] != '02_specific_day':
                    vals['complaint_time'] = None
                else:
                    if (('complaint_time' not in vals) or
                       (not vals['complaint_time'])):
                        vals['complaint_time'] = \
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if 'complainant_name' in vals and vals['complainant_name']:
                new_val = self.encrypt_data(vals['complainant_name'],
                                            self._cipher_key)
                vals['complainant_name'] = new_val
            if 'complainant_email' in vals and vals['complainant_email']:
                new_val = self.encrypt_data(vals['complainant_email'],
                                            self._cipher_key)
                vals['complainant_email'] = new_val
            if 'complainant_vat' in vals and vals['complainant_vat']:
                new_val = self.encrypt_data(vals['complainant_vat'],
                                            self._cipher_key)
                vals['complainant_vat'] = new_val
            if 'complainant_phone' in vals and vals['complainant_phone']:
                new_val = self.encrypt_data(vals['complainant_phone'],
                                            self._cipher_key)
                vals['complainant_phone'] = new_val
            if 'witness_name' in vals and vals['witness_name']:
                new_val = self.encrypt_data(vals['witness_name'],
                                            self._cipher_key)
                vals['witness_name'] = new_val
            if (('complaint_lang' not in vals) or
               vals['complaint_lang'] == ''):
                vals['complaint_lang'] = self.env.user.lang
        return vals

    @api.model
    def _compact_document_fields(self, vals, is_create=False):
        if ('document_01' in vals or 'document_02' in vals or
                'document_03' in vals or 'document_04' in vals or
                'document_05' in vals or 'document_06' in vals):
            value_document_01 = None
            value_document_01_name = None
            if 'document_01' in vals:
                value_document_01 = vals['document_01']
                value_document_01_name = vals['document_01_name']
            elif not is_create:
                value_document_01 = self.document_01
                value_document_01_name = self.document_01_name
            value_document_02 = None
            value_document_02_name = None
            if 'document_02' in vals:
                value_document_02 = vals['document_02']
                value_document_02_name = vals['document_02_name']
            elif not is_create:
                value_document_02 = self.document_02
                value_document_02_name = self.document_02_name
            value_document_03 = None
            value_document_03_name = None
            if 'document_03' in vals:
                value_document_03 = vals['document_03']
                value_document_03_name = vals['document_03_name']
            elif not is_create:
                value_document_03 = self.document_03
                value_document_03_name = self.document_03_name
            value_document_04 = None
            value_document_04_name = None
            if 'document_04' in vals:
                value_document_04 = vals['document_04']
                value_document_04_name = vals['document_04_name']
            elif not is_create:
                value_document_04 = self.document_04
                value_document_04_name = self.document_04_name
            value_document_05 = None
            value_document_05_name = None
            if 'document_05' in vals:
                value_document_05 = vals['document_05']
                value_document_05_name = vals['document_05_name']
            elif not is_create:
                value_document_05 = self.document_05
                value_document_05_name = self.document_05_name
            value_document_06 = None
            value_document_06_name = None
            if 'document_06' in vals:
                value_document_06 = vals['document_06']
                value_document_06_name = vals['document_06_name']
            elif not is_create:
                value_document_06 = self.document_06
                value_document_06_name = self.document_06_name
            values = []
            if value_document_01:
                values.append({'document': value_document_01,
                               'document_name': value_document_01_name, })
            if value_document_02:
                values.append({'document': value_document_02,
                               'document_name': value_document_02_name, })
            if value_document_03:
                values.append({'document': value_document_03,
                               'document_name': value_document_03_name, })
            if value_document_04:
                values.append({'document': value_document_04,
                               'document_name': value_document_04_name, })
            if value_document_05:
                values.append({'document': value_document_05,
                               'document_name': value_document_05_name, })
            if value_document_06:
                values.append({'document': value_document_06,
                               'document_name': value_document_06_name, })
            number_of_values = len(values)
            for i in range(number_of_values):
                field_document = 'document_01'
                field_document_name = 'document_01_name'
                if i == 1:
                    field_document = 'document_02'
                    field_document_name = 'document_02_name'
                elif i == 2:
                    field_document = 'document_03'
                    field_document_name = 'document_03_name'
                elif i == 3:
                    field_document = 'document_04'
                    field_document_name = 'document_04_name'
                elif i == 4:
                    field_document = 'document_05'
                    field_document_name = 'document_05_name'
                elif i == 5:
                    field_document = 'document_06'
                    field_document_name = 'document_06_name'
                vals[field_document] = values[i]['document']
                vals[field_document_name] = values[i]['document_name']
            if number_of_values < self.MAX_DOCUMENTS:
                for i in reversed(range(number_of_values, self.MAX_DOCUMENTS)):
                    field_document = 'document_06'
                    field_document_name = 'document_06_name'
                    if i == 4:
                        field_document = 'document_05'
                        field_document_name = 'document_05_name'
                    elif i == 3:
                        field_document = 'document_04'
                        field_document_name = 'document_04_name'
                    elif i == 2:
                        field_document = 'document_03'
                        field_document_name = 'document_03_name'
                    elif i == 1:
                        field_document = 'document_02'
                        field_document_name = 'document_02_name'
                    elif i == 0:
                        field_document = 'document_01'
                        field_document_name = 'document_01_name'
                    vals[field_document] = None
                    vals[field_document_name] = None
        return vals

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        self.env['ir.ui.view'].clear_caches()
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type in ['form', 'tree']:
            if (not self.env.user.has_group(
               'cim_complaints_channel.group_cim_settings')):
                if view_type == 'tree':
                    nodes = arch.xpath('//tree')
                    for node in nodes:
                        node.set('create', '0')
                else:
                    nodes = arch.xpath('//form')
                    for node in nodes:
                        node.set('create', '0')
        return arch, view

    @api.model
    def fields_get(self, *args, **kwargs):
        fields_to_hide = ['complainant_name', 'link_type_id',
                          'complainant_email', 'complainant_phone',
                          'complainant_vat', 'witness_name', 'tracking_code',
                          'document_01', 'document_02', 'document_03',
                          'document_04', 'document_05', 'document_06', ]
        res = super().fields_get(*args, **kwargs)
        for field_to_hide in fields_to_hide:
            if field_to_hide in res:
                data_of_field = res[field_to_hide]
                if ('searchable' in data_of_field and
                   data_of_field['searchable']):
                    data_of_field['selectable'] = False
                    data_of_field['sortable'] = False
        return res

    def unlink(self):
        for record in self:
            if not (record.is_delegated or record.is_rejected):
                raise exceptions.UserError(_(
                    'It is not possile to delete a in force complaint.'))
            if not record.user_in_group_cim_settings:
                raise exceptions.UserError(_(
                    'You do not have permission to execute this action.'))
        return super().unlink()

    def action_get_communications(self):
        self.ensure_one()
        current_complaint = self
        id_tree_view = self.env.ref(
            'cim_complaints_channel.cim_complaint_communication_view_tree').id
        id_form_view = self.env.ref(
            'cim_complaints_channel.cim_complaint_communication_view_form').id
        search_view = self.env.ref(
            'cim_complaints_channel.cim_complaint_communication_view_search')
        act_window = {
            'type': 'ir.actions.act_window',
            'name': _('Communications'),
            'res_model': 'cim.complaint.communication',
            'view_type': 'form',
            'view_mode': 'form,tree',
            'views': [(id_tree_view, 'tree'), (id_form_view, 'form')],
            'search_view_id': [search_view.id],
            'target': 'current',
            'domain': [('complaint_id', '=', current_complaint.id)],
            'context': {'default_complaint_id': current_complaint.id,
                        'default_from_complainant': False,
                        'from_backend': True,
                        'default_state': '01_draft',
                        'communication_show_complete_code': False, },
            }
        return act_window

    def action_go_to_state_02_admitted(self):
        self.ensure_one()
        if self.state == '01_received' and not self.is_rejected:
            self.state = '02_admitted'
            self._create_communication()

    def action_reject(self):
        self.ensure_one()
        if self.state == '01_received':
            act_window = {
                'type': 'ir.actions.act_window',
                'name': _('Complaint') + ' : ' + self.name,
                'res_model': 'wizard.reject.complaint',
                'src_model': 'cim.complaint',
                'view_mode': 'form',
                'target': 'new',
            }
            return act_window

    def action_readmit(self):
        self.ensure_one()
        if self.is_rejected:
            self.is_rejected = False

    def reject_multiple(self):
        for complaint in self:
            if not complaint.is_rejected:
                if complaint.state != '01_received':
                    raise exceptions.UserError(_(
                        'It is only possible to reject complaints '
                        'in the \'RECEIVED\' state.'))
                complaint.write({
                    'is_rejected': True,
                    'rejection_cause': _('Incomplete information.'),
                    })
                complaint._create_communication()

    def action_go_to_state_03_in_progress(self):
        self.ensure_one()
        if self.state == '02_admitted' and not self.is_rejected:
            vals = {'state': '03_in_progress', }
            if not self.investigating_user_id:
                vals['investigating_user_id'] = self.env.user.id
            self.write(vals)
            if self.automatic_email_state:
                self._create_communication()

    def action_go_to_state_04_ready(self):
        self.ensure_one()
        if self.state == '03_in_progress' and not self.is_rejected:
            self.state = '04_ready'

    def action_go_to_state_05_resolved(self):
        self.ensure_one()
        if self.state == '04_ready' and not self.is_rejected:
            act_window = {
                'type': 'ir.actions.act_window',
                'name': _('Complaint') + ' : ' + self.name,
                'res_model': 'wizard.resolve.complaint',
                'src_model': 'cim.complaint',
                'view_mode': 'form',
                'target': 'new',
            }
            return act_window

    def action_undo(self):
        self.ensure_one()
        if self.state == '02_admitted':
            self.state = '01_received'
        elif self.state == '03_in_progress':
            self.state = '02_admitted'
            if self.is_extended:
                self.is_extended = False
        elif self.state == '04_ready':
            self.state = '03_in_progress'
        elif self.state == '05_resolved':
            self.state = '04_ready'
        if (self.state != '01_received' and self.state != '04_ready' and
           self.automatic_email_state):
            self._create_communication()

    @api.model
    def encrypt_data(self, data_to_encrypt, cipher_key):
        resp = ''
        if data_to_encrypt and cipher_key:
            # Adaptation for 16-multiple
            block_size = AES.block_size
            data_to_encrypt = data_to_encrypt.encode('utf-8')
            len_of_data_to_encrypt = len(data_to_encrypt)
            rest = len_of_data_to_encrypt % block_size
            if rest > 0:
                data_to_encrypt = data_to_encrypt + b' ' * (block_size - rest)
            # Encrypt
            iv = Random.new().read(AES.block_size)
            cipher = AES.new(cipher_key.encode('utf-8'), AES.MODE_CBC, iv)
            encrypted_data = cipher.encrypt(data_to_encrypt)
            # Coding to base64
            resp = base64.b64encode(iv + encrypted_data)
        return resp

    @api.model
    def decrypt_data(self, encrypted_data, cipher_key):
        resp = ''
        if encrypted_data and cipher_key:
            block_size = AES.block_size
            # Decoding from base64
            encrypted_content = base64.b64decode(encrypted_data)
            # Extract iv and encrypted data without iv
            iv = encrypted_content[:block_size]
            encrypted_data = encrypted_content[block_size:]
            # Decrypt
            cipher = AES.new(cipher_key.encode('utf-8'), AES.MODE_CBC, iv)
            raw_decrypted_data = cipher.decrypt(encrypted_data)
            resp = raw_decrypted_data.rstrip()
        return resp

    def action_complainant_data(self):
        self.ensure_one()
        if (self.is_delegated and self.state != '05_resolved' and
           (not self.is_rejected)):
            act_window = {
                'type': 'ir.actions.act_window',
                'name': _('Complaint') + ' : ' + self.name,
                'res_model': 'wizard.complainant.data',
                'src_model': 'cim.complaint',
                'view_mode': 'form',
                'target': 'new',
            }
            return act_window

    def action_extend(self):
        self.ensure_one()
        if self.state == '03_in_progress' and (not self.is_extended):
            self.is_extended = True
            self._create_communication(extension=True)

    def _create_communication(self, extension=False):
        self.ensure_one()
        vals = {
            'complaint_id': self.id,
            'from_complainant': False,
            'state': '02_validated', }
        issue = _('Communication of complaint') + ' ' + self.name
        description = '-'
        if extension:
            issue = _('Extended instruction period')
            description = \
                _('Due to the special complexity of the case, '
                  'the investigation phase is being extended. '
                  'New response deadline:') + ' ' + \
                self._get_date_str(self.deadline_date) + '.'
        else:
            if self.is_rejected:
                issue = _('Complaint rejected')
                description = _('Reason:') + ' ' + self.rejection_cause
            else:
                if self.state == '02_admitted':
                    issue = \
                        _('Acknowledgement of receipt of the complaint filed')
                    description = \
                        _('You have received an acknowledgement of receipt of '
                          'your complaint. A preliminary analysis of its '
                          'admissibility will then be carried out. You are '
                          'also informed that the deadline for completing the '
                          'investigation of the complaint is the following '
                          'date: ') \
                        + self._get_date_str(self.deadline_date) + '.'
                if self.state == '03_in_progress':
                    issue = _('Instruction phase begins')
                    description = \
                        _('The assigned investigating user is:') + ' ' + \
                        self.investigating_user_id.name
                if self.state == '05_resolved':
                    issue = _('Resolution of the complaint')
                    description = self.resolution_text
        vals['issue'] = issue
        vals['description'] = description
        new_communication = \
            self.env['cim.complaint.communication'].with_context(
                from_backend=True).create(vals)
        if new_communication.automatic_email_validate_com:
            new_communication.send_mails()

    def _get_date_str(self, raw_date):
        resp = str(raw_date)
        lang = 'es_ES'
        if 'lang' in self.env.context and self.env.context['lang']:
            lang = self.env.context['lang']
        lang_model = self.env['res.lang'].search([('code', '=', lang)])
        if lang_model:
            resp = raw_date.strftime(lang_model.date_format)
        return resp

    def create_initial_communication(self):
        for record in self:
            issue = _('New complaint:') + ' ' + record.name
            vals = {
                'complaint_id': record.id,
                'issue': issue,
                'from_complainant': True,
                'state': '02_validated', }
            description = _('COMPLAINT ISSUE:') + '\n\n' + \
                record.complaint_type_id.name + ': ' + \
                self._refine_text(record.issue) + '\n\n' + \
                _('FACTS DENUNCED:') + '\n\n' + \
                self._refine_text(record.description)
            if record.defendant_name:
                description = description + '\n\n' + _('DEFENDANT:') + \
                    '\n\n' + self._refine_text(record.defendant_name)
            vals['description'] = description
            if record.is_delegated:
                vals['from_complainant'] = False
            if record.document_01:
                vals['document_01'] = record.document_01
                vals['document_01_name'] = record.document_01_name
            if record.document_02:
                vals['document_02'] = record.document_02
                vals['document_02_name'] = record.document_02_name
            if record.document_03:
                vals['document_03'] = record.document_03
                vals['document_03_name'] = record.document_03_name
            if record.document_04:
                vals['document_04'] = record.document_04
                vals['document_04_name'] = record.document_04_name
            if record.document_05:
                vals['document_05'] = record.document_05
                vals['document_05_name'] = record.document_05_name
            if record.document_06:
                vals['document_06'] = record.document_06
                vals['document_06_name'] = record.document_06_name
            self.env['cim.complaint.communication'].create(vals)

    def _refine_text(self, str_to_refine):
        resp = str_to_refine
        if resp and resp[-1] != '.':
            resp = resp + '.'
        return resp


class CimComplaintCommunication(models.Model):
    _name = 'cim.complaint.communication'
    _description = 'Communication of complaint'
    _inherit = 'mail.thread'
    _order = 'name'

    SIZE_COMMUNICATION_NUMBER = 4
    EMPTY_TRACKING_CODE = '-'

    def _default_communication_number(self):
        resp = 1
        id_of_complaint = 0
        try:
            id_of_complaint = self.env.context['default_complaint_id']
        except Exception:
            id_of_complaint = 0
        if id_of_complaint:
            last_communication = \
                self.env['cim.complaint.communication'].search(
                    [('complaint_id', '=', id_of_complaint)],
                    limit=1, order='communication_number desc')
            if last_communication:
                last_communication = last_communication[0]
                resp = last_communication.communication_number + 1
        return resp

    def _default_processor_user_id(self):
        resp = None
        from_backend = False
        try:
            from_backend = self.env.context['from_backend']
        except Exception:
            from_backend = False
        if from_backend:
            resp = self.env.user.id
        return resp

    complaint_id = fields.Many2one(
        string='Complaint',
        comodel_name='cim.complaint',
        index=True,
        ondelete='cascade',)

    communication_number = fields.Integer(
        string='Communication Number',
        default=_default_communication_number,
        index=True,
        required=True,)

    name = fields.Char(
        string='Identifier of communication',
        size=CimComplaint.SIZE_MEDIUM,
        store=True,
        index=True,
        compute='_compute_name',)

    issue = fields.Char(
        string='Issue',
        size=CimComplaint.SIZE_MEDIUM_EXTRA,
        required=True,
        index=True,
        tracking=True,)

    description = fields.Text(
        string='Communication Data',
        required=True,
        index=True,
        tracking=True,)

    from_complainant = fields.Boolean(
        string='Communication from the complainant',
        default=True,
        readonly=True,)

    from_complainant_as_text = fields.Text(
        string='Communication from the complainant (as text)',
        compute='_compute_from_complainant_as_text',)

    user_in_group_cim_settings = fields.Boolean(
        string='Is a complaints administrator?',
        compute='_compute_user_in_group_cim_settings', )

    processor_user_id = fields.Many2one(
        string='Processor',
        comodel_name='res.users',
        default=_default_processor_user_id,
        readonly=True,
        index=True,)

    decrypted_complainant_email = fields.Char(
        string='Decrypted complainant e-mail',
        related='complaint_id.decrypted_complainant_email',)

    with_email = fields.Boolean(
        string='With e-mail',
        compute='_compute_with_email',)

    automatic_email_validate_com = fields.Boolean(
        string='E-mail to complainant after validate communication (y/n)',
        compute='_compute_automatic_email_validate_com',)

    automatic_email_complainant_com = fields.Boolean(
        string='Send the complainant a copy of your communications (y/n)',
        compute='_compute_automatic_email_complainant_com',)

    state = fields.Selection(
        string="State",
        selection=[
            ('01_draft',
             'Draft'),
            ('02_validated',
             'Validated'),
        ],
        default='02_validated',
        required=True,
        index=True,
        tracking=True,)

    communication_date = fields.Date(
        string='Communication Date',
        store=True,
        compute='_compute_communication_date',
        index=True,)

    document_01 = fields.Binary(
        string='Attachment 1',
        attachment=True,)

    document_01_name = fields.Char(
        string='Name of the attachment 1',)

    document_02 = fields.Binary(
        string='Attachment 2',
        attachment=True,)

    document_02_name = fields.Char(
        string='Name of the attachment 2',)

    document_03 = fields.Binary(
        string='Attachment 3',
        attachment=True,)

    document_03_name = fields.Char(
        string='Name of the attachment 3',)

    document_04 = fields.Binary(
        string='Attachment 4',
        attachment=True,)

    document_04_name = fields.Char(
        string='Name of the attachment 4',)

    document_05 = fields.Binary(
        string='Attachment 5',
        attachment=True,)

    document_05_name = fields.Char(
        string='Name of the attachment 5',)

    document_06 = fields.Binary(
        string='Attachment 6',
        attachment=True,)

    document_06_name = fields.Char(
        string='Name of the attachment 6',)

    number_of_attachments = fields.Integer(
        string='Number of attachments',
        compute='_compute_number_of_attachments',)

    is_sent = fields.Boolean(
        string='Communication Sent',
        default=False,
        readonly=True,)

    icon_inputoutput = fields.Binary(
        string='Icon for input/output',
        compute='_compute_icon_inputoutput')

    notes = fields.Html(
        string='Notes',)

    decrypted_tracking_code = fields.Char(
        string='Tracking Code',
        size=CimComplaint.SIZE_BIG,
        required=True,)

    description_as_html = fields.Char(
        string='Communication Data (as html)',
        compute='_compute_description_as_html',)

    _sql_constraints = [
        ('valid_communication_number',
         'CHECK (communication_number > 0)',
         'The communication number must be a positive value.'),
        ('name_unique',
         'UNIQUE (name)',
         'Existing communication.'),
        ]

    @api.depends('complaint_id', 'communication_number')
    def _compute_name(self):
        for record in self:
            name = ''
            if record.complaint_id and record.communication_number:
                name = record.complaint_id.name + '-' + \
                    str(record.communication_number).zfill(
                        self.SIZE_COMMUNICATION_NUMBER)
            record.name = name

    def _compute_from_complainant_as_text(self):
        for record in self:
            from_complainant_as_text = _('Complainant')
            if not record.from_complainant:
                from_complainant_as_text = _('Investigating User')
            record.from_complainant_as_text = from_complainant_as_text

    def _compute_user_in_group_cim_settings(self):
        user_in_group_cim_settings = \
            self.env.user.has_group(
                'cim_complaints_channel.group_cim_settings')
        for record in self:
            record.user_in_group_cim_settings = user_in_group_cim_settings

    def _compute_with_email(self):
        for record in self:
            with_email = False
            if record.complaint_id and record.complaint_id.complainant_email:
                with_email = True
            record.with_email = with_email

    def _compute_automatic_email_validate_com(self):
        config = self.env['ir.config_parameter'].sudo()
        automatic_email_validate_com = config.get_param(
            'cim_complaints_channel.automatic_email_validate_com', False)
        for record in self:
            record.automatic_email_validate_com = automatic_email_validate_com

    def _compute_automatic_email_complainant_com(self):
        config = self.env['ir.config_parameter'].sudo()
        automatic_email_complainant_com = config.get_param(
            'cim_complaints_channel.automatic_email_complainant_com', False)
        for record in self:
            record.automatic_email_complainant_com = \
                automatic_email_complainant_com

    @api.depends('state')
    def _compute_communication_date(self):
        for record in self:
            communication_date = None
            if record.state == '02_validated':
                communication_date = fields.Datetime.now()
            record.communication_date = communication_date

    def _compute_number_of_attachments(self):
        for record in self:
            number_of_attachments = CimComplaint.MAX_DOCUMENTS
            if not record.document_06_name:
                number_of_attachments = number_of_attachments - 1
                if not record.document_05_name:
                    number_of_attachments = number_of_attachments - 1
                    if not record.document_04_name:
                        number_of_attachments = number_of_attachments - 1
                        if not record.document_03_name:
                            number_of_attachments = number_of_attachments - 1
                            if not record.document_02_name:
                                number_of_attachments = \
                                        number_of_attachments - 1
                                if not record.document_01_name:
                                    number_of_attachments = \
                                            number_of_attachments - 1
            record.number_of_attachments = number_of_attachments

    def _compute_icon_inputoutput(self):
        image_path_input = \
            modules.module.get_resource_path('cim_complaints_channel',
                                             'static/img', 'icon_right.png')
        image_path_output = \
            modules.module.get_resource_path('cim_complaints_channel',
                                             'static/img', 'icon_left.png')
        for record in self:
            icon_inputoutput = None
            image_path = None
            if record.from_complainant:
                image_path = image_path_input
            else:
                image_path = image_path_output
            if image_path:
                image_file = open(image_path, 'rb')
                icon_inputoutput = base64.b64encode(image_file.read())
            record.icon_inputoutput = icon_inputoutput

    def _compute_description_as_html(self):
        for record in self:
            description_as_html = ''
            if record.description:
                description_as_html = self._convert_text_to_html(
                    record.description)
            record.description_as_html = description_as_html

    @api.constrains('complaint_id', 'communication_number')
    def _check_complaint_id(self):
        for record in self:
            if ((not record.complaint_id) or
               (not record.communication_number)):
                raise exceptions.ValidationError(
                    _('It is mandatory to enter the complaint of the '
                      'communication.'))

    def name_get(self):
        result = []
        # communication_show_complete_code
        communication_show_complete_code = \
            self.env.context.get('communication_show_complete_code', True)
        for record in self:
            display_name = record.name
            if record.complaint_id and record.communication_number:
                if communication_show_complete_code:
                    display_name = _('Complaint') + ' ' + \
                        record.complaint_id.name + ', ' + \
                        _('communication #') + ' ' + \
                        str(record.communication_number)
                else:
                    display_name = _('#') + ' ' + \
                        str(record.communication_number)
            result.append((record.id, display_name))
        return result

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals = self._test_tracking_code(vals)
            vals = self._process_vals(vals, is_create=True)
        new_communications = super().create(vals_list)
        for new_communication in new_communications:
            if new_communication.from_complainant:
                if new_communication.automatic_email_complainant_com:
                    new_communication.send_mails()
                if new_communication.complaint_id.param_email_for_notice:
                    self._send_notice(new_communication)
        return new_communications

    def write(self, vals):
        vals = self._process_vals(vals)
        super().write(vals)
        return True

    @api.model
    def _test_tracking_code(self, vals):
        if vals:
            if 'decrypted_tracking_code' not in vals:
                vals['decrypted_tracking_code'] = self.EMPTY_TRACKING_CODE
            if (vals['decrypted_tracking_code'] != self.EMPTY_TRACKING_CODE and
               ('complaint_id' not in vals)):
                model_cim_complaint = self.env['cim.complaint']
                complaints = model_cim_complaint.search([], order='id desc')
                for complaint in (complaints or []):
                    decrypted_tracking_code_of_complaint = \
                        model_cim_complaint.decrypt_data(
                            complaint.tracking_code,
                            model_cim_complaint._cipher_key)
                    if (vals['decrypted_tracking_code'] ==
                            decrypted_tracking_code_of_complaint.decode()):
                        vals['complaint_id'] = complaint.id
                        vals['decrypted_tracking_code'] = \
                            self.EMPTY_TRACKING_CODE
                        break
        return vals

    @api.model
    def _process_vals(self, vals, is_create=False):
        if vals:
            if (is_create and ('document_01_name' in vals) and
               ('document_01' not in vals)):
                vals.pop('document_01_name')
            if (is_create and ('document_02_name' in vals) and
               ('document_02' not in vals)):
                vals.pop('document_02_name')
            if (is_create and ('document_03_name' in vals) and
               ('document_03' not in vals)):
                vals.pop('document_03_name')
            if (is_create and ('document_04_name' in vals) and
               ('document_04' not in vals)):
                vals.pop('document_04_name')
            if (is_create and ('document_05_name' in vals) and
               ('document_05' not in vals)):
                vals.pop('document_05_name')
            if (is_create and ('document_06_name' in vals) and
               ('document_06' not in vals)):
                vals.pop('document_06_name')
            if ((is_create or len(self) == 1) and
                    ('document_01' in vals or 'document_02' in vals or
                     'document_03' in vals or 'document_04' in vals or
                     'document_05' in vals or 'document_06' in vals)):
                vals = self._compact_document_fields(vals, is_create)
            if is_create and 'complaint_id' in vals and vals['complaint_id']:
                communication_number = 1
                last_communication = \
                    self.env['cim.complaint.communication'].search(
                        [('complaint_id', '=', vals['complaint_id'])],
                        limit=1, order='communication_number desc')
                if last_communication:
                    last_communication = last_communication[0]
                    communication_number = \
                        last_communication.communication_number + 1
                vals['communication_number'] = communication_number
        return vals

    @api.model
    def _compact_document_fields(self, vals, is_create=False):
        if ('document_01' in vals or 'document_02' in vals or
                'document_03' in vals or 'document_04' in vals or
                'document_05' in vals or 'document_06' in vals):
            value_document_01 = None
            value_document_01_name = None
            if 'document_01' in vals:
                value_document_01 = vals['document_01']
                value_document_01_name = vals['document_01_name']
            elif not is_create:
                value_document_01 = self.document_01
                value_document_01_name = self.document_01_name
            value_document_02 = None
            value_document_02_name = None
            if 'document_02' in vals:
                value_document_02 = vals['document_02']
                value_document_02_name = vals['document_02_name']
            elif not is_create:
                value_document_02 = self.document_02
                value_document_02_name = self.document_02_name
            value_document_03 = None
            value_document_03_name = None
            if 'document_03' in vals:
                value_document_03 = vals['document_03']
                value_document_03_name = vals['document_03_name']
            elif not is_create:
                value_document_03 = self.document_03
                value_document_03_name = self.document_03_name
            value_document_04 = None
            value_document_04_name = None
            if 'document_04' in vals:
                value_document_04 = vals['document_04']
                value_document_04_name = vals['document_04_name']
            elif not is_create:
                value_document_04 = self.document_04
                value_document_04_name = self.document_04_name
            value_document_05 = None
            value_document_05_name = None
            if 'document_05' in vals:
                value_document_05 = vals['document_05']
                value_document_05_name = vals['document_05_name']
            elif not is_create:
                value_document_05 = self.document_05
                value_document_05_name = self.document_05_name
            value_document_06 = None
            value_document_06_name = None
            if 'document_06' in vals:
                value_document_06 = vals['document_06']
                value_document_06_name = vals['document_06_name']
            elif not is_create:
                value_document_06 = self.document_06
                value_document_06_name = self.document_06_name
            values = []
            if value_document_01:
                values.append({'document': value_document_01,
                               'document_name': value_document_01_name, })
            if value_document_02:
                values.append({'document': value_document_02,
                               'document_name': value_document_02_name, })
            if value_document_03:
                values.append({'document': value_document_03,
                               'document_name': value_document_03_name, })
            if value_document_04:
                values.append({'document': value_document_04,
                               'document_name': value_document_04_name, })
            if value_document_05:
                values.append({'document': value_document_05,
                               'document_name': value_document_05_name, })
            if value_document_06:
                values.append({'document': value_document_06,
                               'document_name': value_document_06_name, })
            number_of_values = len(values)
            for i in range(number_of_values):
                field_document = 'document_01'
                field_document_name = 'document_01_name'
                if i == 1:
                    field_document = 'document_02'
                    field_document_name = 'document_02_name'
                elif i == 2:
                    field_document = 'document_03'
                    field_document_name = 'document_03_name'
                elif i == 3:
                    field_document = 'document_04'
                    field_document_name = 'document_04_name'
                elif i == 4:
                    field_document = 'document_05'
                    field_document_name = 'document_05_name'
                elif i == 5:
                    field_document = 'document_06'
                    field_document_name = 'document_06_name'
                vals[field_document] = values[i]['document']
                vals[field_document_name] = values[i]['document_name']
            if number_of_values < CimComplaint.MAX_DOCUMENTS:
                for i in reversed(range(number_of_values,
                                        CimComplaint.MAX_DOCUMENTS)):
                    field_document = 'document_06'
                    field_document_name = 'document_06_name'
                    if i == 4:
                        field_document = 'document_05'
                        field_document_name = 'document_05_name'
                    elif i == 3:
                        field_document = 'document_04'
                        field_document_name = 'document_04_name'
                    elif i == 2:
                        field_document = 'document_03'
                        field_document_name = 'document_03_name'
                    elif i == 1:
                        field_document = 'document_02'
                        field_document_name = 'document_02_name'
                    elif i == 0:
                        field_document = 'document_01'
                        field_document_name = 'document_01_name'
                    vals[field_document] = None
                    vals[field_document_name] = None
        return vals

    def unlink(self):
        for record in self:
            if record.state != '01_draft':
                raise exceptions.UserError(_(
                    'It is not possile to delete a validated communication.'))
            if record.complaint_id.state in ('04_ready', '05_resolved'):
                raise exceptions.UserError(_(
                    'The complaint has completed its investigation phase, '
                    'so it is no longer possible to delete communications.'))
        return super().unlink()

    def action_go_to_state_02_validated(self):
        self.ensure_one()
        communication = self
        if communication.state == '01_draft':
            communication.state = '02_validated'
            if communication.automatic_email_validate_com:
                communication.send_mails()

    def action_undo(self):
        self.ensure_one()
        if self.state == '02_validated':
            self.state = '01_draft'

    def action_send_mail(self):
        self.ensure_one()
        communication = self
        if (communication and communication.state == '02_validated' and
           communication.with_email):
            communication.send_mails()

    def send_mails(self):
        for record in self:
            complainant_email = record.complaint_id.decrypted_complainant_email
            if record.state == '02_validated' and complainant_email:
                text_for_log_ok = _('Email sent. Destination:')
                text_for_log_fail = _('ERROR, the email could not be sent. '
                                      'Destination:')
                mail_ok = self._send_communication(record)
                if mail_ok:
                    record.is_sent = True
                    message_ok = text_for_log_ok + ' ' + complainant_email
                    record.message_post(body=message_ok)
                else:
                    message_fail = text_for_log_fail + ' ' + complainant_email
                    record.message_post(body=message_fail)

    @api.model
    def _send_communication(self, communication):
        resp = True
        mail_template_communication = None
        try:
            mail_template_communication = self.env.ref(
                'cim_complaints_channel.'
                'mail_template_communication').sudo()
        except Exception:
            mail_template_communication = None
        if mail_template_communication:
            user_lang = 'en_US'
            if communication.complaint_id.complaint_lang:
                user_lang = communication.complaint_id.complaint_lang
            try:
                mail_template_communication.with_context(
                    lang=user_lang).send_mail(
                        communication.id, force_send=True)
            except Exception:
                resp = False
        else:
            resp = False
        return resp

    @api.model
    def _send_notice(self, communication):
        resp = True
        mail_template_notice = None
        try:
            mail_template_notice = self.env.ref(
                'cim_complaints_channel.'
                'mail_template_notice').sudo()
        except Exception:
            mail_template_notice = None
        if mail_template_notice:
            user_lang = 'en_US'
            if communication.complaint_id.complaint_lang:
                user_lang = communication.complaint_id.complaint_lang
            try:
                mail_template_notice.with_context(
                    lang=user_lang).send_mail(
                        communication.id, force_send=True)
            except Exception:
                resp = False
        else:
            resp = False
        return resp

    @api.model
    def _convert_text_to_html(self, text):
        html = ''
        if text:
            html = text.replace('\n', '<br/>')
            html = '<span>' + html + '</span>'
        return html
