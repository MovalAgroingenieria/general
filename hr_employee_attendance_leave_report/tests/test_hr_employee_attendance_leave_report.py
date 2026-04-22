# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# pylint: disable=invalid-name

from datetime import date, timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("hr_employee_attendance_leave_report")
class TestHrEmployeeAttendanceLeaveReport(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env[
            "report.hr_employee_attendance_leave_report.att_lea_template"
        ]
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "ReportTestLeaveType",
                "requires_allocation": "no",
                "leave_validation_type": "no_validation",
            }
        )
        cls.employee = cls.env["hr.employee"].create({"name": "ReportTestEmployee"})
        cls.leave_day = date(2030, 3, 11)
        cls.public_day = date(2030, 4, 15)

    def test_get_report_values_requires_form(self):
        with self.assertRaises(UserError):
            self.report._get_report_values([], data={})

    def test_get_public_holidays_data(self):
        public_year = self.env["calendar.public.holiday"].create(
            {"year": self.public_day.year}
        )
        self.env["calendar.public.holiday.line"].create(
            {
                "name": "ReportTestPublicHoliday",
                "date": self.public_day,
                "public_holiday_id": public_year.id,
            }
        )
        start = fields.Datetime.to_datetime(self.public_day)
        end = start + timedelta(days=1)
        rows = self.report._get_public_holidays_data(start, end)
        self.assertTrue(rows)
        self.assertIn("holiday_name", rows[0])

    def test_get_attendance_data_returns_list_and_meta(self):
        start = fields.Datetime.to_datetime(self.leave_day)
        end = start + timedelta(days=1)
        rows, meta = self.report._get_attendance_data(self.employee.id, start, end)
        self.assertIsInstance(rows, list)
        self.assertIsInstance(meta, dict)
        self.assertIn("show_extras", meta)
        self.assertIn("extra_col_count", meta)

    def test_get_leaves_data_domain(self):
        self.env["hr.leave"].create(
            {
                "name": "ReportTestLeave",
                "employee_id": self.employee.id,
                "holiday_status_id": self.leave_type.id,
                "request_date_from": self.leave_day,
                "request_date_to": self.leave_day,
            }
        )
        start = fields.Datetime.to_datetime(self.leave_day)
        end = start + timedelta(days=1)
        rows = self.report._get_leaves_data(self.employee.id, start, end)
        self.assertTrue(rows)

    def test_wizard_defaults_from_context(self):
        wiz = (
            self.env["attendance.leave.wizard"]
            .with_context(active_ids=self.employee.ids)
            .create(
                {
                    "start_date": fields.Datetime.to_datetime(self.leave_day),
                    "end_date": fields.Datetime.to_datetime(self.leave_day)
                    + timedelta(days=1),
                }
            )
        )
        self.assertEqual(wiz.number_of_selected_employees, 1)
        self.assertIn(self.employee, wiz.employee_ids)
