# -*- coding: utf-8 -*-
# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api


class ResEomConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    _name = 'res.eom.config.settings'
    _description = 'Configuration of the electronic office'

    editable_notes = fields.Boolean(
        string='Editable Notes (y/n)',
        default=True,
        required=True,
        help='Ability to edit internal annotations',)

    def set_default_values(self):
        values = self.env['ir.default'].sudo()
        values.set('res.eom.config.settings',
                   'editable_notes',
                   self.editable_notes)
