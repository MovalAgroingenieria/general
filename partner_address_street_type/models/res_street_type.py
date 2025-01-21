# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields


class ResStreetType(models.Model):
    _name = "res.street.type"
    _description = "Types of street"

    name = fields.Char(
        string="Street Type",
        required=True)

    abbreviation = fields.Char(
        string="Abbreviation",
        required=True)

    show_in_list = fields.Boolean(
        string='Show in list',
        default=True)

    is_default = fields.Boolean(
        string='Default Type',
        default=False)

    def name_get(self):
        result = []
        if self.env.context.get('in_combo', False):
            for record in self:
                result.append((record.id,
                               record.abbreviation + ' - ' + record.name))
        else:
            for record in self:
                result.append((record.id, record.abbreviation))
        return result

    _sql_constraints = [
        ("unique_street_type", "UNIQUE (name)",
         "Existing street type."),
        ]
