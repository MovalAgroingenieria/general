# -*- coding: utf-8 -*-
# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    _description = 'Configuration of the electronic office'

    editable_notes = fields.Boolean(
        string='Editable Notes (y/n)',
        required=True,
        help='Ability to edit internal annotations',
        config_parameter='eom_authdnie.editable_notes')
