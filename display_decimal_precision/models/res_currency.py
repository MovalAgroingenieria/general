# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import math

from odoo import api, fields, models


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    display_rounding = fields.Float('Display Rounding Factor', digits=(12, 6))
    display_decimal_places = fields.Integer(
        compute='_get_display_decimal_places')

    @api.depends('rounding', 'display_rounding')
    def _get_display_decimal_places(self):
        for record in self:
            if not record.display_rounding:
                record.display_decimal_places = record.decimal_places
            elif 0 < record.display_rounding < 1:
                record.display_decimal_places = \
                    int(math.ceil(math.log10(1 / record.display_rounding)))
            else:
                record.display_decimal_places = 0
