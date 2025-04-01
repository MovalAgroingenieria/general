# -*- coding: utf-8 -*-
# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
import random
import string
import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, modules, exceptions, tools, _


class EomElectronicfileCommunication(models.Model):
    _name = 'eom.electronicfile.communication'
    _description = 'Electronic File Communication'
    _inherit = 'mail.thread'

    SIZE_CSV_CODE = 16

    def _get_default_notification_deadline(self):
        notification_deadline_days = self.env[
            'ir.config_parameter'].sudo().get_param(
                'eom_eoffice.notification_deadline')
        return notification_deadline_days

    electronicfile_id = fields.Many2one(
        string='Electronic File',
        comodel_name='eom.electronicfile',
        required=True,
        index=True,
        readonly=True)

    communication_number = fields.Integer(
        string='Communication Number',
        required=True,
        index=True,
        readonly=True)

    name = fields.Char(
        string='Identifier',
        required=True,
        index=True,
        store=True,
        readonly=True)

    issue = fields.Char(
        string='Issue',
        required=True,
        index=True)

    communication_text = fields.Html(
        string='Text')

    is_notification = fields.Boolean(
        string='Notification (y/n)',
        readonly=True)

    email = fields.Char(
        string='Email',
        compute='_compute_email')

    mobile = fields.Char(
        string='Mobile',
        compute='_compute_mobile')

    number_of_attachments = fields.Integer(
        string='Number of attachments',
        compute='_compute_number_of_attachments')

    state = fields.Selection(
        string="State",
        required=True,
        selection=[
            ('01_draft', 'Draft'),
            ('02_validated', 'Validated'),
            ('03_readed', 'Readed'),
            ('04_rejected', 'Rejected')],
        default='01_draft')

    validation_time = fields.Datetime(
        string='Validation Time',
        store=True,
        compute='_compute_validation_time')

    reading_time = fields.Datetime(
        string='Reading Time',
        store=True,
        compute='_compute_reading_time')

    notification_deadline_date = fields.Datetime(
        string='Notification Deadline Date',
        compute='_compute_notification_deadline_date',
    )

    rejection_time = fields.Datetime(
        string='Rejection Time',
        store=True,
        compute='_compute_rejection_time')

    notification_deadline = fields.Integer(
        string='Notification Deadline',
        default=_get_default_notification_deadline,
    )

    expired_deadline = fields.Boolean(
        string='Deadline Exceeded',
        readonly=True,
        compute='_compute_expired_deadline',
        search='_search_expired_deadline')

    show_expired_deadline = fields.Boolean(
        string='Show Deadline Exceeded',
        compute='_compute_show_expired_deadline')

    document = fields.Binary(
        string='Notification',
        readonly=True,
        attachment=True)

    document_name = fields.Char(
        string='Document Name',
        readonly=True)

    csv_code = fields.Char(
        string='CSV Code',
        store=True,
        readonly=True)

    notes = fields.Html(
        string='Notes')

    icon_notification_or_entry = fields.Binary(
        string='Icon Notificacion or Entry',
        compute='_compute_icon_notification_or_entry')

    _sql_constraints = [
        ('name_unique',
         'UNIQUE (name)',
         'Existing electronic file communication name (repeated identifier).'),
        ]

    @api.depends('electronicfile_id')
    def _compute_email(self):
        for record in self:
            email = ""
            postal_notification = \
                record.electronicfile_id.digitalregister_id.postal_notification
            if not postal_notification:
                email = record.electronicfile_id.\
                    digitalregister_id.notification_email
            record.email = email

    @api.depends('electronicfile_id')
    def _compute_mobile(self):
        for record in self:
            record.mobile = record.electronicfile_id.\
                digitalregister_id.notification_mobile

    def name_get(self):
        result = []
        show_complete_code = self.env.context.get('show_complete_code', True)
        for record in self:
            if show_complete_code:
                display_name = record.name
            else:
                communication_number = record.communication_number or 0
                display_name = _('Num. ') + str(communication_number)
            result.append((record.id, display_name))
        return result

    def _compute_number_of_attachments(self):
        for record in self:
            attachments = self.env['ir.attachment'].search(
                [('res_model', '=', 'eom.electronicfile.communication'),
                 ('res_id', '=', record.id)])
            record.number_of_attachments = len(attachments)

    def _compute_notification_deadline(self):
        notification_deadline_days = self.env[
            'ir.config_parameter'].sudo().get_param(
                'eom_eoffice.notification_deadline')
        for record in self:
            record.notification_deadline = notification_deadline_days

    def action_go_to_state_02_validated(self):
        self.ensure_one()
        pdf = False
        if self.state == '01_draft':
            self.state = '02_validated'
            report_name = 'eom_eoffice.notification_report'
            pdf = self.env['ir.actions.report'].get_pdf([self.id], report_name)
            if pdf:
                document_name = self.name.replace('/', '_') + '.pdf'
                self.write({
                    'name': self.name,
                    'csv_code': self.csv_code,
                    'issue': self.issue,
                    'communication_text': self.communication_text,
                    'document': base64.encodebytes(pdf),
                    'document_name': document_name,
                })
            digitalregister = self.electronicfile_id.digitalregister_id
            postal_notification = digitalregister.postal_notification
            if not postal_notification:
                mail_template_communication_state = None
                partner = False
                try:
                    mail_template_communication_state = self.env.ref(
                        'eom_eoffice.mail_template_notification_validated').\
                        sudo()
                except Exception:
                    mail_template_communication_state = None
                if mail_template_communication_state:
                    partner = digitalregister.partner_id
                    if partner and partner.lang:
                        doc_lang = partner.lang
                    elif self.env.user.lang:
                        doc_lang = self.env.user.lang
                    else:
                        doc_lang = 'en_US'
                    mail_template_communication_state.with_context(
                        lang=doc_lang).send_mail(
                            self.id, force_send=True)

    def action_return_to_state_01_draft(self):
        self.ensure_one()
        if self.state == '02_validated':
            self.state = '01_draft'

    def action_mark_as_rejected(self):
        self.ensure_one()
        if self.state == '02_validated' or self.state == '03_readed':
            self.state = '04_rejected'

    def action_mark_as_readed(self):
        self.ensure_one()
        if self.state == '02_validated':
            self.state = '03_readed'

    def _compute_icon_notification_or_entry(self):
        image_path_is_notification = modules.module.get_resource_path(
            'eom_eoffice', 'static/img', 'icon_notification.png')
        image_path_is_entry = modules.module.get_resource_path(
            'eom_eoffice', 'static/img', 'icon_entry.png')
        for record in self:
            icon = None
            image_path = None
            if record.is_notification:
                image_path = image_path_is_notification
            else:
                image_path = image_path_is_entry
            if image_path:
                image_file = open(image_path, 'rb')
                icon = base64.b64encode(image_file.read())
            record.icon_notification_or_entry = icon

    def _compute_notification_deadline_date(self):
        for record in self:
            notification_deadline_date = None
            if record.is_notification and record.validation_time and \
                    record.state not in ['03_readed']:
                notification_deadline_date = \
                    fields.Datetime.from_string(record.validation_time) + \
                    relativedelta(days=record.notification_deadline)
            record.notification_deadline_date = notification_deadline_date

    def _compute_expired_deadline(self):
        date_now = fields.Datetime.now()
        deadline_days = self.env[
            'ir.config_parameter'].sudo().get_param(
                'eom_eoffice.notification_deadline')
        if not deadline_days:
            raise exceptions.ValidationError(
                _('Notification deadline parameter has not been set.'))
        for record in self:
            expired_deadline = False
            if record.is_notification and record.validation_time and \
                    record.state not in ['03_readed']:
                notification_deadline_date = record.notification_deadline_date
                if notification_deadline_date < date_now:
                    expired_deadline = True
            record.expired_deadline = expired_deadline

    @api.depends('expired_deadline')
    def _compute_show_expired_deadline(self):
        for record in self:
            show_expired_deadline = False
            if (record.state in ('01_draft', '02_validated') and
                    record.expired_deadline):
                show_expired_deadline = True
            record.show_expired_deadline = show_expired_deadline

    @api.model
    def _search_expired_deadline(self, operator, value):
        electronicfile_communications_ids = []
        operator_of_filter = 'in'
        if operator == '!=':
            operator_of_filter = 'not in'
        where_clause = """
            WHERE  is_notification AND (validation_time + INTERVAL '1 day' *
                                        notification_deadline) < NOW()
              AND (state != '03_readed')"""
        sql_statement = 'SELECT id FROM eom_electronicfile_communication ' \
            + where_clause
        sql_resp = False
        try:
            self.env.cr.savepoint()
            self.env.cr.execute(sql_statement)
            sql_resp = self.env.cr.fetchall()
        except Exception:
            self.env.cr.rollback()
        if sql_resp:
            for item in sql_resp:
                electronicfile_communications_ids.append(item[0])
        return [('id', operator_of_filter, electronicfile_communications_ids)]

    @api.constrains('state', 'communication_text')
    def _check_communication_text(self):
        filled = False
        html_field = self.communication_text
        communication_model = self.env['eom.electronicfile.communication']
        state_str = communication_model._fields['state'].convert_to_export(
            self.state, self)
        if self.state == '02_validated':
            if html_field and tools.html2plaintext(html_field).strip():
                filled = True
            if not filled:
                raise exceptions.ValidationError(
                    _('At the present state (%s) the Text is mandatory.')
                    % (state_str))

    @api.constrains('electronicfile_id')
    def _check_eletronicfile_state(self):
        if self.electronicfile_id.state == '03_resolved':
            raise exceptions.ValidationError(
                _('A notification cannot be created for a Resolved File.'))

    def write(self, vals):
        if 'state' in vals:
            if vals['state'] == '01_draft':
                vals['csv_code'] = False
                vals['document_name'] = False
                vals['document'] = False
            if vals['state'] == '02_validated':
                # Validation time
                vals['validation_time'] = datetime.strftime(
                    datetime.now(), '%Y-%m-%d %H:%M:%S')
                if self.is_notification:
                    vals['csv_code'] = self._get_csv_code()
            elif vals['state'] == '03_readed':
                # Reading time
                vals['reading_time'] = datetime.strftime(
                    datetime.now(), '%Y-%m-%d %H:%M:%S')
            elif vals['state'] == '04_rejected':
                vals['rejection_time'] = datetime.strftime(
                    datetime.now(), '%Y-%m-%d %H:%M:%S')
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'is_notification' not in vals:
                vals['is_notification'] = True
            # CSV code
            if (
                'state' in vals
                and vals['state'] == '02_validated'
                and vals['is_notification']
            ):
                vals['csv_code'] = self._get_csv_code()
            # Electronicfile
            if 'electronicfile_id' in vals:
                electronicfile_id = vals['electronicfile_id']
            elif self.env.context.get('default_electronicfile_id'):
                electronicfile_id = self.env.context.get(
                                    'default_electronicfile_id')
            # Communication number
            next_communication_number = 0
            communications = self.search(
                [('electronicfile_id', '=', electronicfile_id)]
            )
            num_communications = len(communications)
            next_communication_number = (
                num_communications + 1 if num_communications else 1
            )
            vals['communication_number'] = next_communication_number
            # Name (identifier)
            electronicfile = self.env['eom.electronicfile'].search(
                [('id', '=', electronicfile_id)], limit=1
            )
            identifier = (
                electronicfile.name
                + '-'
                + str(vals['communication_number']).zfill(4)
            )
            vals['name'] = identifier
        return super().create(vals_list)

    def unlink(self):
        for record in self:
            state = record.electronicfile_id.state
            if state == '03_resolved':
                raise exceptions.UserError(_(
                    'It is not possile to delete a Comunication of a '
                    'resolved File.'))
        return super().unlink()

    def _generate_random_csv_code(self):
        character_set = string.ascii_letters + string.digits
        length = self.SIZE_CSV_CODE
        random_csv_code = ''.join(
            random.choice(character_set) for _ in range(length))
        return random_csv_code

    def _check_unicity_csv_code(self, csv_code):
        csv_code_exits = False
        sql_statement = """
            SELECT id
              FROM eom_electronicfile_communication
             WHERE csv_code = '%s'""" % (csv_code)
        self.env.cr.execute(sql_statement)
        sql_resp = self.env.cr.fetchall()
        if len(sql_resp) > 0:
            csv_code_exits = True
        return csv_code_exits

    def _get_csv_code(self):
        csv_code = False
        csv_code_ok = False
        while not csv_code_ok:
            csv_code = self._generate_random_csv_code()
            csv_code_exits = self._check_unicity_csv_code(csv_code)
            if not csv_code_exits:
                csv_code_ok = True
        return csv_code

    def _set_notification_as_rejected_cron(self):
        _logger = logging.getLogger(self.__class__.__name__)
        expired_notifications = \
            self.env['eom.electronicfile.communication'].search(
                [('expired_deadline', '=', True),
                 ('is_notification', '=', True)])
        if len(expired_notifications) > 0:
            for expired_notification in expired_notifications:
                _logger.info('Setting notification %s as rejected'
                             % (expired_notification.name))
                expired_notification.state = '04_rejected'
                expired_notification.rejection_time = datetime.strftime(
                    datetime.now(), '%Y-%m-%d %H:%M:%S')
