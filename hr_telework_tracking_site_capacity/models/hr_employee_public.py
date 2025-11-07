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

    monday_preference = fields.Selection(
        related="employee_id.monday_preference",
        readonly=True,
        store=False,
    )

    tuesday_preference = fields.Selection(
        related="employee_id.tuesday_preference",
        readonly=True,
        store=False,
    )

    wednesday_preference = fields.Selection(
        related="employee_id.wednesday_preference",
        readonly=True,
        store=False,
    )

    thursday_preference = fields.Selection(
        related="employee_id.thursday_preference",
        readonly=True,
        store=False,
    )

    friday_preference = fields.Selection(
        related="employee_id.friday_preference",
        readonly=True,
        store=False,
    )

    preferred_workstation_ids = fields.Many2many(
        related="employee_id.preferred_workstation_ids",
        readonly=True,
        store=False,
    )

    primary_workstation_id = fields.Many2one(
        related="employee_id.primary_workstation_id",
        readonly=True,
        store=False,
    )

    telework_day_ids = fields.One2many(
        related="employee_id.telework_day_ids",
        readonly=True,
        store=False,
    )
