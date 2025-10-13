# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    default_capacity_full_day = fields.Integer(
        string='Default Capacity (Full Day)',
        help='If there is no specific rule or weekly pattern, '
             'this capacity is used.',
        default=30
    )
