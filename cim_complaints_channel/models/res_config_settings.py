# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, exceptions, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sequence_complaint_code_id = fields.Many2one(
        string='Sequence for the codes of complaints',
        comodel_name='ir.sequence',
        config_parameter="cim_complaints_channel.sequence_complaint_code_id",
        help='Default values of the complaint codes',)

    length_tracking_code = fields.Integer(
        string='Length of the tracking code (number of characters)',
        default=10,
        required=True,
        config_parameter="cim_complaints_channel.length_tracking_code",
        help='Tracking code length to identify complainants '
             '(number of characters)',)

    acknowledgement_period = fields.Integer(
        string='Acknowledgement period for the complaint admission',
        default=7,
        required=True,
        config_parameter="cim_complaints_channel.acknowledgement_period",
        help='Acknowledgement period for the complaint admission '
             '(number of days)',)

    automatic_email_state = fields.Boolean(
        string='E-mail to complainant after change state of complaint (y/n)',
        default=False,
        required=True,
        config_parameter="cim_complaints_channel.automatic_email_state",
        help='Send e-mail to complainant after change the state of the '
             'complaint',)

    automatic_email_validate_com = fields.Boolean(
        string='E-mail to complainant after validate communication (y/n)',
        default=False,
        required=True,
        config_parameter="cim_complaints_channel.automatic_email_validate_com",
        help='Send e-mail to complainant after validate the communication',)

    automatic_email_complainant_com = fields.Boolean(
        string='Send the complainant a copy of your communications (y/n)',
        default=False,
        required=True,
        config_parameter="cim_complaints_channel."
                         "automatic_email_complainant_com",
        help='Send e-mail to complainant a copy of your communications',)

    notice_period = fields.Integer(
        string='Notice Period (number of days)',
        default=10,
        required=True,
        config_parameter="cim_complaints_channel.notice_period",
        help='Notice period before the complaint deadline (number of days)',)

    deadline = fields.Integer(
        string='Deadline (number of months)',
        default=1,
        required=True,
        config_parameter="cim_complaints_channel.deadline",
        help='Complaint deadline (number of months)',)

    deadline_extended = fields.Integer(
        string='Extended Deadline (number of months)',
        default=1,
        required=True,
        config_parameter="cim_complaints_channel.deadline_extended",
        help='Extended complaint deadline (number of months)',)

    email_for_notice = fields.Char(
        string='E-mail for notice',
        config_parameter="cim_complaints_channel.email_for_notice",)

    _sql_constraints = [
        ('valid_length_tracking_code',
         'CHECK (length_tracking_code > 0)',
         'The length of tracking code must be a positive value.'),
        ('valid_notice_period',
         'CHECK (notice_period >= 0)',
         'The notice period cannot have a negative value.'),
        ('valid_deadline',
         'CHECK (deadline > 0)',
         'The deadline must be a positive value.'),
        ('valid_deadline_extended',
         'CHECK (deadline_extended > 0)',
         'The extended deadline must be a positive value.'),
        ]

    @api.constrains('deadline', 'deadline_extended')
    def _check_state_selected(self):
        for record in self:
            if (record.deadline and record.deadline_extended and
               record.deadline_extended < record.deadline):
                raise exceptions.UserError(_(
                    'The extended deadline can not be less than the '
                    'predetermined deadline.'))
