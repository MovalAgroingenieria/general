# -*- coding: utf-8 -*-
# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sequence_electronicfile_code_id = fields.Many2one(
        string='Sequence for the codes of electronic files',
        comodel_name='ir.sequence',
        help='Default values of the electronic file codes',)

    deadline = fields.Integer(
        string='Deadline (months)',
        help='Number of months for resolution within the deadline.')

    max_size_attachments = fields.Integer(
        string='Max. size attachments (MB)',
        help='The maximal size of attachments (in Megabytes).')

    notification_deadline = fields.Integer(
        string='Notification Deadline (days)',
        help='Number of days to read a notification.')

    sign_certificate_path = fields.Char(
        string="Certificate file path",
        help="Path to PKCS#12 certificate file")

    sign_certificate_password_path = fields.Char(
        string="Password file path",
        help="Path to certificate password file")

    def set_default_values(self):
        super().set_default_values()
        values = self.env['ir.default'].sudo()
        values.set('res.config.settings',
                   'sequence_electronicfile_code_id',
                   self.sequence_electronicfile_code_id.id)
        values.set('res.config.settings',
                   'deadline', self.deadline)
        values.set('res.config.settings',
                   'max_size_attachments', self.max_size_attachments)
        values.set('res.config.settings',
                   'notification_deadline', self.notification_deadline)
        values.set('res.config.settings',
                   'sign_certificate_path', self.sign_certificate_path)
        values.set('res.config.settings',
                   'sign_certificate_password_path',
                   self.sign_certificate_password_path)
