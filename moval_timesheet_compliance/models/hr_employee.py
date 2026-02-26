# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    x_timesheet_compliance_excluded = fields.Boolean(
        string="Excluded from timesheet compliance",
        default=False,
        help="If set, this employee is excluded from daily compliance computation, "
             "emails (B1/B2/B3) and escalation. Use for roles not required to report timesheets.",
    )
