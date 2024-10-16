# -*- coding: utf-8 -*-
# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, modules, exceptions, _


class EomElectronicfile(models.Model):
    _name = 'eom.electronicfile'
    _description = 'Electronic File'

    SIZE_NAME = 25

    def _default_name(self):
        resp = None
        sequence_electronicfile_code_id = self.env['ir.values'].get_default(
            'res.eom.config.settings', 'sequence_electronicfile_code_id')
        if sequence_electronicfile_code_id:
            model_ir_sequence = self.env['ir.sequence'].sudo()
            sequence_electronicfile_code = \
                model_ir_sequence.browse(sequence_electronicfile_code_id)
            if sequence_electronicfile_code:
                resp = model_ir_sequence.next_by_code(
                    sequence_electronicfile_code.code)
        return resp

    event_time = fields.Datetime(
        string='Time',
        default=lambda self: fields.datetime.now(),
        required=True,
        index=True,
        readonly=True,)

    digitalregister_id = fields.Many2one(
        string='Digital Certificate',
        comodel_name='eom.digitalregister',
        required=True,
        index=True,
        readonly=True,
        ondelete='restrict',)

    name = fields.Char(
        string='Code',
        size=SIZE_NAME,
        default=_default_name,
        required=True,
        index=True,)

    partner_id = fields.Many2one(
        string='Partner',
        comodel_name='res.partner',
        store=True,
        index=True,
        compute='_compute_partner_id',
        ondelete='restrict',)

    type = fields.Selection(
        string="Type",
        selection=[
            ('01_generic_instance', 'Generic Instance'),
            ('02_suggestion', 'Suggestion'),
        ],
        default='01_generic_instance',
        required=True,
        index=True,)

    exposition = fields.Text(
        string='Exposition',
        index=True,)

    request = fields.Text(
        string='Request')

    suggestion = fields.Text(
        string='Suggestion')

    firstname = fields.Char(
        string='First Name',
        store=True,
        compute='_compute_firstname',
        index=True,)

    lastname = fields.Char(
        string='Last Name',
        store=True,
        compute='_compute_lastname',
        index=True,)

    fullname = fields.Char(
        string='Full Name',
        store=True,
        compute='_compute_fullname',
        index=True,)

    editable_notes = fields.Boolean(
        string='Editable Notes (y/n)',
        compute='_compute_editable_notes',)

    notes = fields.Html(
        string='Notes',)

    sia_code = fields.Char(
        string='SIA Code',
        compute='_compute_sia_code')

    state = fields.Selection(
        string="State",
        selection=[
            ('01_received', 'Received'),
            ('02_in_progress', 'In progress'),
            ('03_resolved', 'Resolved')],
        default='01_received')

    deadline_date = fields.Datetime(
        string='Deadline',
        compute='_compute_deadline_date')

    expired_deadline = fields.Boolean(
        string='Expired Deadline',
        compute='_compute_expired_deadline')

    icon_warning_expired_deadline = fields.Binary(
        string='Icon warning expired deadline',
        compute='_compute_icon_warning_expired_deadline')

    technician_id = fields.Many2one(
        string='Technician',
        comodel_name='res.users',
        index=True)

    resolution = fields.Text(
        string='Resolution',
        index=True)

    number_of_attachmets = fields.Integer(
        string='Number of attachmets',
        compute='_compute_number_of_attachmets')

    communication_ids = fields.One2many(
        string='Communications of the file',
        comodel_name='eom.electronicfile.communication',
        inverse_name='electronicfile_id')

    number_of_communications = fields.Integer(
        string='Number of communications',
        compute='_compute_number_of_communications')

    _sql_constraints = [
        ('name_unique',
         'UNIQUE (name)',
         'Existing electronic file (repeated code).'),
        ]

    @api.depends('digitalregister_id', 'digitalregister_id.partner_id')
    def _compute_partner_id(self):
        for record in self:
            partner_id = None
            if (record.digitalregister_id and
               record.digitalregister_id.partner_id):
                partner_id = record.digitalregister_id.partner_id
            record.partner_id = partner_id

    @api.depends('digitalregister_id', 'digitalregister_id.firstname')
    def _compute_firstname(self):
        for record in self:
            firstname = ''
            if (record.digitalregister_id and
               record.digitalregister_id.firstname):
                firstname = record.digitalregister_id.firstname
            record.firstname = firstname

    @api.depends('digitalregister_id', 'digitalregister_id.lastname')
    def _compute_lastname(self):
        for record in self:
            lastname = ''
            if (record.digitalregister_id and
               record.digitalregister_id.lastname):
                lastname = record.digitalregister_id.lastname
            record.lastname = lastname

    @api.depends('digitalregister_id',
                 'digitalregister_id.firstname', 'digitalregister_id.lastname')
    def _compute_fullname(self):
        for record in self:
            fullname = ''
            if record.digitalregister_id:
                if record.digitalregister_id.lastname:
                    fullname = record.digitalregister_id.lastname
                    if record.digitalregister_id.firstname:
                        fullname = fullname + ' ' + \
                            record.digitalregister_id.firstname
                elif record.digitalregister_id.firstname:
                    fullname = record.digitalregister_id.firstname
            record.fullname = fullname

    @api.multi
    def _compute_editable_notes(self):
        editable_notes = self.env['ir.values'].get_default(
            'res.eom.config.settings', 'editable_notes')
        for record in self:
            record.editable_notes = editable_notes

    def action_show_digitalregister_id(self):
        self.ensure_one()
        id_form_view = self.env.ref(
            'eom_eoffice.eom_digitalregister_view_form').id
        act_window = {
            'type': 'ir.actions.act_window',
            'name': _('Digital Register'),
            'res_model': 'eom.digitalregister',
            'view_type': 'form',
            'view_mode': 'form',
            'views': [(id_form_view, 'form')],
            'target': 'current',
            'res_id': self.digitalregister_id.id
            }
        return act_window

    def action_show_partner_id(self):
        self.ensure_one()
        id_form_view = self.env.ref('eom_authdnie.view_partner_form').id
        act_window = {
            'type': 'ir.actions.act_window',
            'name': _('Partner'),
            'res_model': 'res.partner',
            'view_type': 'form',
            'view_mode': 'form',
            'views': [(id_form_view, 'form')],
            'target': 'current',
            'res_id': self.partner_id.id
            }
        return act_window

    @api.multi
    def _compute_sia_code(self):
        # @TODO
        for record in self:
            pass

    @api.multi
    def _compute_deadline_date(self):
        deadline_months = self.env['ir.values'].get_default(
            'res.eom.config.settings', 'deadline')
        if not deadline_months:
            raise exceptions.ValidationError(
                _('Deadline parameter has not been set.'))
        for record in self:
            event_time_obj = datetime.strptime(
                record.event_time, '%Y-%m-%d %H:%M:%S')
            record.deadline_date = \
                event_time_obj + relativedelta(months=deadline_months)

    @api.multi
    def _compute_expired_deadline(self):
        for record in self:
            pass

    @api.multi
    def _compute_icon_warning_expired_deadline(self):
        image_path_is_expired_deadline_no = modules.module.get_resource_path(
            'eom_eoffice', 'static/img', 'icon_ontime.png')
        image_path_is_expired_deadline_yes = modules.module.get_resource_path(
            'eom_eoffice', 'static/img', 'icon_expirated.png')
        for record in self:
            icon_warning = None
            image_path = None
            if record.expired_deadline:
                image_path = image_path_is_expired_deadline_yes
            else:
                image_path = image_path_is_expired_deadline_no
            if image_path:
                image_file = open(image_path, 'rb')
                icon_warning = base64.b64encode(image_file.read())
            record.icon_warning_expired_deadline = icon_warning

    @api.multi
    def _compute_number_of_attachmets(self):
        for record in self:
            attachments = self.env['ir.attachment'].search(
                [('res_model', '=', 'eom.electronicfile'),
                 ('res_id', '=', record.id)])
            record.number_of_attachmets = len(attachments)

    @api.multi
    def _compute_number_of_communications(self):
        for record in self:
            record.number_of_communications = len(record.communication_ids)

    @api.multi
    def action_go_to_state_02_in_progress(self):
        self.ensure_one()
        if self.state == '01_received':
            self.state = '02_in_progress'

    @api.multi
    def action_return_to_state_01_received(self):
        self.ensure_one()
        if self.state == '02_in_progress':
            self.state = '01_received'

    @api.multi
    def action_go_to_state_03_resolved(self):
        self.ensure_one()
        if self.state == '02_in_progress':
            self.state = '03_resolved'

    @api.multi
    def action_return_to_state_02_in_progress(self):
        self.ensure_one()
        if self.state == '03_resolved':
            self.state = '02_in_progress'

    @api.constrains('technician_id')
    def _check_technician_id(self):
        if self.state != '01_received' and self.technician_id is False:
            raise exceptions.ValidationError(
                _('At the present state (%s), the Technician is mandatory.')
                % (self.state))

    @api.constrains('resolution')
    def _check_resolution(self):
        if self.state == '03_resolved' and self.resolution is False:
            raise exceptions.ValidationError(
                _('The Resolution is mandatory in Resolved state'))

    @api.multi
    def action_communications(self):
        self.ensure_one()
        current_electronicfile = self
        # id_tree_view = self.env.ref(
        #     'eom_eoffice.eom_electronicfile_communication_view_tree').id
        # id_form_view = self.env.ref(
        #     'eom_eoffice.eom_electronicfile_communication_view_form').id
        # search_view = self.env.ref(
        #     'eom_eoffice.eom_electronicfile_communication_view_search')
        # act_window = {
        #     'type': 'ir.actions.act_window',
        #     'name': _('Communitacions'),
        #     'res_model': 'eom.electronicfile.communication',
        #     'view_type': 'form',
        #     'view_mode': 'kanban,form,tree',
        #     'views': [(id_tree_view, 'tree'), (id_form_view, 'form')],
        #     'search_view_id': [search_view.id],
        #     'target': 'current',
        #     'domain': [('electronicfile', '=', current_electronicfile.id)],
        #     'context': {'hide_image': True,
        #                 'search_default_grouped_event_time': True,
        #                 'reduced_register_id': True,
        #                 'reduced_access_id': True, },
        #     }
        # return act_window


class EomElectronicfileCommunication(models.Model):
    _name = 'eom.electronicfile.communication'
    _description = 'Electronic File Communication'

    electronicfile_id = fields.Many2one(
        string='Electronic File',
        comodel_name='eom.electronicfile',
        required=True,
        index=True,
        readonly=True)
