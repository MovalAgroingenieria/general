# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestHrEmployeeCurrentAttendanceTime(TransactionCase):
    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()
        cls.user = cls.env.ref("base.user_admin")
        cls.employee = cls.env["hr.employee"].search(
            [("user_id", "=", cls.user.id)], limit=1
        )
        if not cls.employee:
            cls.employee = cls.env["hr.employee"].create(
                {
                    "name": "Employee Test",
                    "user_id": cls.user.id,
                }
            )

    def test_get_current_attendance_time_no_checkin(self):
        self.employee.last_attendance_id = False
        self.employee.attendance_state = "checked_out"
        result = self.employee.get_current_attendance_time()
        self.assertEqual(result["hours"], 0)
        self.assertEqual(result["minutes"], 0)
        self.assertEqual(result["display"], "0h 0m")

    def test_get_current_attendance_time_checked_in(self):
        now = fields.Datetime.now()
        check_in = now - timedelta(minutes=90)

        self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": check_in,
            }
        )
        # Force recompute of last_attendance_id / attendance_state from DB
        self.employee.invalidate_recordset()

        result = self.employee.get_current_attendance_time()
        self.assertIn("h", result["display"])
        self.assertIn("m", result["display"])

    def test_get_current_attendance_time_no_employee_for_user(self):
        other_user = self.env["res.users"].create(
            {
                "name": "Other User",
                "login": "other_user_login",
                "email": "other@example.com",
            }
        )
        result = (
            self.env["hr.employee"].with_user(other_user).get_current_attendance_time()
        )
        self.assertEqual(result["hours"], 0)
        self.assertEqual(result["minutes"], 0)
        self.assertEqual(result["display"], "0h 0m")
