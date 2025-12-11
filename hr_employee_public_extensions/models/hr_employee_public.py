# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    # Fields from hr_holidays
    leave_manager_id = fields.Many2one(
        'res.users', string='Time Off', readonly=True,
        help='Select the user responsible for approving "Time Off" of this employee.\n'
             'If empty, the approval is done by an Administrator or Approver (determined in settings/users).')

    # Fields from hr_expense
    expense_manager_id = fields.Many2one(
        'res.users', string='Expense', readonly=True,
        help='Select the user responsible for approving "Expense" of this employee.\n'
             'If empty, the approval is done by an Administrator or Approver (determined in settings/users).')

    # Fields from hr_attendance_reason (already defined in hr.employee.base)
    show_reason_on_attendance_screen = fields.Boolean(
        readonly=True, help="Show reason on attendance screen"
    )
    required_reason_on_attendance_screen = fields.Boolean(
        readonly=True, help="Required reason on attendance screen"
    )

    # Field from hr_attendance_report_theoretical_time (should already exist via OCA module)
    theoretical_hours_start_date = fields.Date(
        readonly=True,
        help="Fill this field for setting a manual start date for computing "
        "the theoretical hours independently from the attendances. If "
        "not filled, employee creation date or the calendar start date "
        "will be used (the greatest of both)."
    )