# 2022 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import datetime
from odoo import models, fields, api


class HrEmployeeAttendanceLeaveWizard(models.TransientModel):
    _name = 'attendance.leave.wizard'
    _description = 'Wizard for Attendances / Leaves report'

    def _default_employee_ids(self):
        context = self._context
        active_ids = context.get('active_ids')
        employees = self.env['hr.employee'].search([('id', 'in', active_ids)])
        return employees

    def _default_number_of_selected_employees(self):
        context = self._context
        active_ids = context.get('active_ids')
        return len(active_ids)

    report_date = fields.Datetime(
        string='Report date',
        default=datetime.datetime.now(),
        compute="_compute_report_date")

    start_date = fields.Datetime(
        string='Start date',
        required=True)

    end_date = fields.Datetime(
        string='End date',
        required=True)

    employee_ids = fields.Many2many(
        string="Employees",
        relation="employee_report_employee_rel",
        comodel_name="hr.employee",
        default=_default_employee_ids,
        compute="_compute_employee_ids")

    number_of_selected_employees = fields.Integer(
        string="Num. selected employees",
        readonly=True,
        default=_default_number_of_selected_employees)

    def _compute_report_date(self):
        for record in self:
            record.report_date = datetime.datetime.now()

    def _compute_employee_ids(self):
        active_ids = employees = False
        context = self._context
        active_ids = context.get('active_ids')
        if active_ids:
            employees = self.env['hr.employee'].search(
                [('id', 'in', active_ids)])
        if employees:
            self.employee_ids = employees

    def print_employee_attendance_leave_report(self):
        self.ensure_one()
        [data] = self.read()
        datas = {
            'model': 'hr.employee',
            'form': data
            }
        return self.env.ref(
            'hr_employee_attendance_leave_report.'
            'action_employee_attendance_leave_report'
            ).report_action(self, data=datas)

