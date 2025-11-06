# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    auto_generate_week = fields.Boolean(
        string="Enable automatic generation",
        related="employee_id.auto_generate_week",
        readonly=True,
        store=False,
        help="Auto-generate weekly declarations (readonly, from employee)",
    )
