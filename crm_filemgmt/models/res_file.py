# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import datetime
from jinja2 import Template, TemplateError
from odoo import models, fields, api, SUPERUSER_ID, exceptions, _


class ResFile(models.Model):
    _name = 'res.file'
    _description = "File management"
    _inherit = ['mail.thread', 'simple.model', 'common.format']

    _size_name = 50
    _size_description = 100
    _set_num_code = False

    SIZE_ANNUALSEQ_CODE = 4

    def _default_file_code(self):
        current_year = datetime.datetime.now().year
        file_prefix = self.env['ir.config_parameter'].sudo().get_param(
            f"crm_filemgmt.file_prefix_{self.env.company.id}")
        if not file_prefix:
            raise exceptions.UserError(
                _('The file prefix parameter is not set. '
                  'Go to configuration and set a value for the parameter'))
        file_prefix = file_prefix.strip()
        file_prefix += '-'
        full_prefix = file_prefix + str(current_year).zfill(4) + '/'
        resp = full_prefix + '1'.zfill(self.SIZE_ANNUALSEQ_CODE)
        files = self.search([('name', 'like', full_prefix)], limit=1,
                            order='name desc')
        if len(files) == 1:
            last_code = files[0].name
            if len(last_code) > len(full_prefix):
                numeric_suffix = \
                    last_code[-(len(last_code) - len(full_prefix)):]
                try:
                    proposed_code = int(numeric_suffix)
                except Exception:
                    proposed_code = 0
                if proposed_code > 0:
                    resp = full_prefix + str(proposed_code + 1).zfill(
                        self.SIZE_ANNUALSEQ_CODE)
        return resp

    def _default_category_id(self):
        resp = 0
        proposed_category = self.env.ref(
            'crm_filemgmt.resfilecategory_internal_file')
        if proposed_category:
            resp = proposed_category.id
        return resp

    alphanum_code = fields.Char(
        string='Code',
        size=30,
        default=_default_file_code,
        required=True,
        index=True)

    date_file = fields.Date(
        string='Discharge date',
        default=lambda self: fields.datetime.now(),
        required=True,
        index=True)

    subject = fields.Char(
        string='Subject',
        size=150,
        required=True,
        index=True)

    tag_ids = fields.Many2many(
        string='File Tags',
        comodel_name='res.filetag',
        relation='res_file_filetag_rel',
        column1='file_id', column2='filetag_id')

    image = fields.Binary(
        string='Photo / Image',
        attachment=True)

    stage_id = fields.Many2one(
        string='Stage',
        comodel_name='res.file.stage',
        required=True,
        default=lambda self: self._default_stage_id(),
        group_expand='_read_group_stage_ids',
        tracking=True)

    is_closing_stage = fields.Boolean(
        string='Is Closing Stage',
        store=True,
        compute='_compute_is_closing_stage')

    is_blocked = fields.Boolean(
        string='Blocked',
        default=False,
        tracking=True)

    notes = fields.Html(
        string='Notes')

    category_id = fields.Many2one(
        string='Category',
        comodel_name='res.file.category',
        index=True,
        required=True,
        ondelete='restrict',
        default=_default_category_id)

    partnerlink_ids = fields.One2many(
        string='Partners',
        comodel_name='res.file.partnerlink',
        inverse_name='file_id')

    partner_id = fields.Many2one(
        string='Partner',
        comodel_name='res.partner',
        index=True,
        ondelete='restrict',
        store=True,
        compute='_compute_partner_id',
        tracking=True)

    filelink_ids = fields.One2many(
        string='Files',
        comodel_name='res.file.filelink',
        inverse_name='file_id')

    color = fields.Integer(
        string='Color Index',
        default="0",
        help='0:grey, 1:green, 2:yellow, 3:orange, 4:red, 5:purple, 6:blue, '
             '7:cyan, 8:light-green, 9:magenta')

    closing_date = fields.Date(
        string='Closing date',
        store=True,
        compute="_compute_closing_date")

    container_id = fields.Many2one(
        string='Container',
        comodel_name='res.file.container')

    file_attachment_ids = fields.One2many(
        string="File attachments",
        comodel_name="ir.attachment",
        compute="_compute_attachments_ids")

    has_filelinks = fields.Boolean(
        string='Has filelinks',
        default=False,
        compute="_compute_has_filelinks")

    has_attachments = fields.Boolean(
        string='Has attachments',
        default=False,
        compute="_compute_has_attachments")

    technician_id = fields.Many2one(
        string='Technician',
        comodel_name='res.partner',
        index=True)

    with_technician = fields.Boolean(
        string='With technician',
        default=False,
        store=True,
        compute="_compute_with_technician")

    file_top_comment_template_id = fields.Many2one(
        'base.comment.template',
        string='Top Comment Template')

    file_bottom_comment_template_id = fields.Many2one(
        'base.comment.template',
        string='Bottom Comment Template')

    file_top_comment = fields.Html(
        string='Top comment',
        translate=True)

    file_bottom_comment = fields.Html(
        string='Bottom comment',
        translate=True)

    active = fields.Boolean(
        default=True)

    file_report_id = fields.Many2one(
        string="Report",
        comodel_name='res.file.report')

    template_start = fields.Html(
        string='Template start')

    template_end = fields.Html(
        string='Template end')

    template_start_rendered = fields.Html(
        string='Template start rendered',
        compute='_compute_template_start_rendered')

    template_end_rendered = fields.Html(
        string='Template end rendered',
        compute='_compute_template_end_rendered')

    _sql_constraints = [
        ('unique_name', 'UNIQUE (name)', 'Existing file code.'),
    ]

    def action_block_file(self):
        self.ensure_one()
        self.is_blocked = True

    def action_unblock_file(self):
        self.ensure_one()
        self.is_blocked = False

    def name_get(self):
        result = []
        for record in self:
            if record.subject:
                name = record.name + ' ' + '[' + record.subject + ']'
            else:
                name = record.name + ' ' + _('[no subject]')
            result.append((record.id, name))
        return result

    def _compute_attachments_ids(self):
        for record in self:
            record.file_attachment_ids = record.env['ir.attachment'].search(
                [('res_model', '=', record._name), ('res_id', '=', record.id)])

    @api.depends('partnerlink_ids')
    def _compute_partner_id(self):
        for record in self:
            partner_id = None
            for partnerlink in record.partnerlink_ids:
                if partnerlink.is_main:
                    partner_id = partnerlink.partner_id
                    break
            record.partner_id = partner_id

    @api.depends('stage_id')
    def _compute_is_closing_stage(self):
        for record in self:
            record.is_closing_stage = record.stage_id.is_closing_stage

    @api.depends('stage_id')
    def _compute_closing_date(self):
        for record in self:
            if record.is_closing_stage:
                record.closing_date = datetime.datetime.now()
            else:
                record.closing_date = False

    @api.depends('filelink_ids')
    def _compute_has_filelinks(self):
        for record in self:
            has_filelinks = False
            if record.filelink_ids:
                has_filelinks = True
            record.has_filelinks = has_filelinks

    @api.depends('file_attachment_ids')
    def _compute_has_attachments(self):
        for record in self:
            has_attachments = False
            if record.file_attachment_ids:
                has_attachments = True
            record.has_attachments = has_attachments

    @api.depends('technician_id')
    def _compute_with_technician(self):
        for record in self:
            with_technician = False
            if record.technician_id:
                with_technician = True
            record.with_technician = with_technician

    @api.model_create_multi
    def create(self, vals):
        # Check filecode format
        if 'alphanum_code' in vals[0]:
            self. _check_filecode_format(vals[0]['alphanum_code'])

        new_file = super().create(vals)
        return new_file

    def _check_filecode_format(self, filecode):
        file_prefix = self.env['ir.config_parameter'].sudo().get_param(
            f"crm_filemgmt.file_prefix_{self.env.company.id}").strip()
        file_prefix += '-'

        # Check prefix is separated by a hyphen
        after_prefix = filecode[len(file_prefix)-1:]
        if not after_prefix.startswith('-'):
            raise exceptions.UserError(
                _('The prefix must be separated from the rest of the file '
                  'name by a hyphen (-).'))

        # Check file name slashs
        if '/' in filecode:
            if filecode.startswith('/') or filecode.endswith('/'):
                raise exceptions.UserError(
                    _('The file name cannot start or end with a slash (/).'))
            count = 0
            for i in filecode:
                if i == '/':
                    count += 1
            if count > 1:
                raise exceptions.UserError(
                    _('There are more than one backslash in the file name.'))
            try:
                file_number = int(filecode.split('/')[1])
            except Exception:
                raise exceptions.UserError(
                    _('The file number must be an integer, found: %s')
                    % file_number)

    @api.model
    def _default_stage_id(self):
        return self.env['res.file.stage'].search([], limit=1)

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        stage_ids = stages._search([], order=order,
                                   access_rights_uid=SUPERUSER_ID)
        return stages.browse(stage_ids)

    @api.constrains('partnerlink_ids')
    def _check_partnerlink_ids(self):
        if len(self) == 1:
            file = self
            if file.partnerlink_ids:
                main_partnerlinks = file.partnerlink_ids.filtered(
                    lambda x: x.is_main)
                if main_partnerlinks:
                    if len(main_partnerlinks) == 0:
                        raise exceptions.UserError(
                            _('It is mandatory to check the primary partner.'))
                    if len(main_partnerlinks) > 1:
                        raise exceptions.UserError(
                            _('Only one primary partner is allowed.'))
            unique_ids_of_partner = []
            for partnerlink in file.partnerlink_ids:
                unique_ids_of_partner.append(partnerlink.partner_id.id)
            unique_ids_of_partner = list(set(unique_ids_of_partner))
            if len(unique_ids_of_partner) != len(file.partnerlink_ids):
                raise exceptions.UserError(_('There are repeated partners.'))

    @api.constrains('filelink_ids')
    def _check_filelink_ids(self):
        if len(self) == 1:
            file = self
            if file.filelink_ids:
                self_referenced_file = self.env['res.file.filelink'].search(
                    [('file_id', '=', file.id),
                     (('related_file_id', '=', file.id))])
                if self_referenced_file:
                    raise exceptions.UserError(_('The file cannot be '
                                                 'self-referenced.'))
            unique_ids_of_file = []
            for filelink in file.filelink_ids:
                unique_ids_of_file.append(filelink.related_file_id.id)
            unique_ids_of_file = list(set(unique_ids_of_file))
            if len(unique_ids_of_file) != len(file.filelink_ids):
                raise exceptions.UserError(_('There are repeated files.'))

    def _check_access_file_filemgmt(self):
        access_file_filemgmt = False
        is_filemgmt_portal_group = self.env.user.has_group(
            'crm_filemgmt.group_file_portal')
        is_filemgmt_user_group = self.env.user.has_group(
            'crm_filemgmt.group_file_user')
        if is_filemgmt_portal_group or is_filemgmt_user_group:
            access_file_filemgmt = True
        return access_file_filemgmt

    @api.onchange('file_top_comment_template_id')
    def _set_file_top_comment(self):
        comment = self.file_top_comment_template_id
        if comment:
            self.file_top_comment = comment.get_value(self.partner_id.id)

    @api.onchange('file_bottom_comment_template_id')
    def _set_file_bottom_comment(self):
        comment = self.file_bottom_comment_template_id
        if comment:
            self.file_bottom_comment = comment.get_value(self.partner_id.id)

    @api.onchange('stage_id')
    def _onchange_stage_id(self):
        if (self.stage_id.is_closing_stage and
                not self._origin.stage_id.is_closing_stage):
            raise exceptions.UserError(
                _('You cannot move a file from a non-closing stage '
                  'to a closing stage.'))

    @api.onchange('file_report_id',
                  'file_report_id.report_template_start')
    def _compute_template_start(self):
        for record in self:
            if (record.file_report_id and
                    record.file_report_id.report_template_start):
                record.template_start = \
                    record.file_report_id.report_template_start

    @api.depends('template_start')
    def _compute_template_start_rendered(self):
        for record in self:
            template_start_rendered = ''
            if record.template_start:
                try:
                    template_start = Template(record.template_start)
                    template_start_rendered = template_start.render(
                        record=record)
                except TemplateError as e:
                    template_start_rendered = \
                        '<p style="text-align:center;color:red;">' + \
                        '<b><font style="font-size: 14px;">' + \
                        _('ERROR IN START TEMPLATE') + '</font></b></p>' + \
                        '<p><br>' + e.message + '</p>'
            record.template_start_rendered = template_start_rendered

    @api.onchange('file_report_id',
                  'file_report_id.report_template_end')
    def _compute_template_end(self):
        for record in self:
            if (record.file_report_id and
                    record.file_report_id.report_template_end):
                record.template_end = \
                    record.file_report_id.report_template_end

    @api.depends('template_end')
    def _compute_template_end_rendered(self):
        for record in self:
            template_end_rendered = ''
            if record.template_end:
                try:
                    template_end = Template(record.template_end)
                    template_end_rendered = template_end.render(record=record)
                except TemplateError as e:
                    template_end_rendered = \
                        '<p style="text-align:center;color:red;">' + \
                        '<b><font style="font-size: 14px;">' + \
                        _('ERROR IN END TEMPLATE') + '</font></b></p>' + \
                        '<p><br>' + e.message + '</p>'
            record.template_end_rendered = template_end_rendered

    def action_print_selected_report(self):
        self.ensure_one()
        selected_report = self.file_report_id.iractreportxml_id.xml_id
        if not selected_report:
            raise exceptions.UserError(_('No report has been selected.'))
        return self.env.ref(selected_report).report_action(self)

    def action_get_start_template(self):
        for record in self:
            if (not record.file_report_id or
                    not record.file_report_id.report_template_start):
                raise exceptions.UserError(_(
                    'No report or start template has been selected.'))
            else:
                record.template_start = \
                    record.file_report_id.report_template_start

    def action_get_end_template(self):
        for record in self:
            if (not record.file_report_id or
                    not record.file_report_id.report_template_end):
                raise exceptions.UserError(_(
                    'No report or end template has been selected.'))
            else:
                record.template_end = \
                    record.file_report_id.report_template_end

    # @api.model
    # def _get_view(self, view_id=None, view_type='form', toolbar=False,
    #               submenu=False):
    #     res = super(ResFile, self).fields_view_get(
    #         view_id=view_id, view_type=view_type, toolbar=toolbar,
    #         submenu=submenu)
    #     # Hide actions only to portal users
    #     actions_to_hide = \
    #         ['wua_crm_filemgmt.wua_generate_files_parcel_shp',
    #          'wua_crm_filemgmt.res_file_print_selected_report']
    #     access_to_actions = True
    #     is_filemgmt_portal_group = self.env.user.has_group(
    #         'crm_filemgmt.group_file_portal')
    #     if is_filemgmt_portal_group:
    #         access_to_actions = False
    #     if view_type == 'form':
    #         doc = etree.XML(res['arch'])
    #         if not access_to_actions:
    #             actions_to_show = []
    #             actions_menu = res.get('toolbar', {}).get('action', [])
    #             if actions_menu:
    #                 for action_menu in actions_menu:
    #                     if action_menu['xml_id'] not in actions_to_hide:
    #                         actions_to_show.append(action_menu)
    #                 res['toolbar']['action'] = actions_to_show
    #         res['arch'] = etree.tostring(doc)
    #     return res


class ResFilePartnerlink(models.Model):
    _name = 'res.file.partnerlink'
    _description = "File Parnerlink"

    file_id = fields.Many2one(
        string='File_',
        comodel_name='res.file',
        required=True,
        index=True,
        ondelete='cascade')

    partner_id = fields.Many2one(
        string='Partner',
        comodel_name='res.partner',
        required=True,
        index=True,
        ondelete='restrict')

    is_main = fields.Boolean(
        string='Primary',
        help='If checked, this partner will be the primary')

    subject = fields.Char(
        string='Subject',
        related='file_id.subject')

    date_file = fields.Date(
        string='Discharge date',
        related='file_id.date_file')

    stage_id = fields.Many2one(
        string='Stage',
        related='file_id.stage_id')

    category_id = fields.Many2one(
        string='Category',
        related='file_id.category_id')


class ResFileFilelink(models.Model):
    _name = 'res.file.filelink'
    _description = "File filelink"

    file_id = fields.Many2one(
        string='File_',
        comodel_name='res.file',
        required=True,
        index=True,
        ondelete='cascade')

    related_file_id = fields.Many2one(
        string='Related File',
        comodel_name='res.file',
        required=True,
        ondelete='restrict')

    related_file_subject = fields.Char(
        string='Subject',
        related='related_file_id.subject')

    related_file_category_id = fields.Many2one(
        string='Category',
        related='related_file_id.category_id')
