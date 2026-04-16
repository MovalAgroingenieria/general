# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import datetime

from odoo import api, fields, models


class HrEmployeeAttendanceLeaveWizard(models.TransientModel):
    _name = "attendance.leave.wizard"
    _description = "Wizard for Attendances / Leaves report"

    @api.model
    def _default_employee_ids(self):
        active_ids = self.env.context.get("active_ids") or []
        if not active_ids:
            return self.env["hr.employee"]
        return self.env["hr.employee"].search([("id", "in", active_ids)])

    @api.model
    def _default_number_of_selected_employees(self):
        active_ids = self.env.context.get("active_ids") or []
        return len(active_ids)

    report_date = fields.Datetime(
        string="Report date",
        compute="_compute_report_date",
    )

    start_date = fields.Datetime(string="Start date", required=True)

    end_date = fields.Datetime(string="End date", required=True)

    employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        relation="employee_report_employee_rel",
        string="Employees",
        default=lambda self: self._default_employee_ids(),
    )

    number_of_selected_employees = fields.Integer(
        string="Num. selected employees",
        readonly=True,
        default=lambda self: self._default_number_of_selected_employees(),
    )

    def _compute_report_date(self):
        now = datetime.datetime.now()
        for record in self:
            record.report_date = now

    def print_employee_attendance_leave_report(self):
        self.ensure_one()
        data = self.read()[0]
        datas = {
            "model": "hr.employee",
            "form": data,
        }
        return self.env.ref(
            "hr_employee_attendance_leave_report."
            "action_employee_attendance_leave_report"
        ).report_action(self, data=datas)
