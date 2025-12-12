# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models, tools


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    # Missing fields that cause hr_employee_public view errors
    # These fields exist in hr.employee but are missing from hr.employee.public

    leave_manager_id = fields.Many2one(
        'res.users', string='Time Off', readonly=True,
        help='Select the user responsible for approving "Time Off" of this employee.\n'
             'If empty, the approval is done by an Administrator or Approver (determined in settings/users).')

    expense_manager_id = fields.Many2one(
        'res.users', string='Expense', readonly=True,
        help='Select the user responsible for approving "Expense" of this employee.\n'
             'If empty, the approval is done by an Administrator or Approver (determined in settings/users).')

    show_reason_on_attendance_screen = fields.Boolean(
        readonly=True, help="Show reason on attendance screen"
    )
    required_reason_on_attendance_screen = fields.Boolean(
        readonly=True, help="Required reason on attendance screen"
    )

    theoretical_hours_start_date = fields.Date(
        readonly=True,
        help="Fill this field for setting a manual start date for computing "
        "the theoretical hours independently from the attendances. If "
        "not filled, employee creation date or the calendar start date "
        "will be used (the greatest of both)."
    )