# -*- coding: utf-8 -*-
# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sequence_electronicfile_code_id = fields.Many2one(
        string='Sequence for the codes of electronic files',
        comodel_name='ir.sequence',
        help='Default values of the electronic file codes',
        config_parameter='eom_eoffice.sequence_electronicfile_code_id')

    deadline = fields.Integer(
        string='Deadline (months)',
        help='Number of months for resolution within the deadline.',
        config_parameter='eom_eoffice.deadline')

    max_size_attachments = fields.Integer(
        string='Max. size attachments (MB)',
        help='The maximal size of attachments (in Megabytes).',
        config_parameter='eom_eoffice.max_size_attachments')

    notification_deadline = fields.Integer(
        string='Notification Deadline (days)',
        help='Number of days to read a notification.',
        config_parameter='eom_eoffice.notification_deadline')

    sign_certificate_path = fields.Char(
        string="Certificate file path",
        help="Path to PKCS#12 certificate file",
        config_parameter='eom_eoffice.sign_certificate_path')

    sign_certificate_password_path = fields.Char(
        string="Password file path",
        help="Path to certificate password file",
        config_parameter='eom_eoffice.sign_certificate_password_path')
