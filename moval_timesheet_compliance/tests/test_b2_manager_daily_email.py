# Copyright 2026 Moval
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta
from unittest.mock import patch

from odoo import fields

from .common import TimesheetComplianceCase
from odoo.tests import tagged


@tagged("-at_install")
class TestComplianceDailyB2Manager(TimesheetComplianceCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Compliance = cls.env["timesheet.compliance"]
        cls.Department = cls.env["hr.department"]
        cls.Users = cls.env["res.users"]
        cls.Employees = cls.env["hr.employee"]

        cls.env["ir.config_parameter"].sudo().set_param(
            "web.base.url", "http://example.com"
        )

        cls.target_date = fields.Date.context_today(cls.env.user) - timedelta(days=1)

        cls.manager_user = cls.Users.create(
            {
                "name": "Manager B2",
                "login": "manager_b2",
                "email": "manager_b2@example.com",
                "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.manager_employee = cls.Employees.create(
            {
                "name": "Manager Employee B2",
                "user_id": cls.manager_user.id,
            }
        )

        cls.department = cls.Department.create(
            {
                "name": "Department B2",
                "manager_id": cls.manager_employee.id,
            }
        )

        cls.user = cls.Users.create(
            {
                "name": "User B2",
                "login": "user_b2",
                "email": "user_b2@example.com",
                "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.employee = cls.Employees.create(
            {
                "name": "Employee B2",
                "user_id": cls.user.id,
                "department_id": cls.department.id,
            }
        )

        # Second employee in same department (needed to test grouping)
        cls.user2 = cls.Users.create(
            {
                "name": "User B2-2",
                "login": "user_b2_2",
                "email": "user_b2_2@example.com",
                "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.employee2 = cls.Employees.create(
            {
                "name": "Employee B2-2",
                "user_id": cls.user2.id,
                "department_id": cls.department.id,
            }
        )

    def _create_incident(self, employee=None, **vals):
        employee = employee or self.employee
        return self.Compliance.create(
            {
                "employee_id": employee.id,
                "department_id": self.department.id,
                "date": self.target_date,
                "telework": False,
                "state": "warn",
                "attendance_hours": 8.0,
                "timesheet_hours": 6.0,
                "delta_hours": 2.0,
                "generic_hours": 0.0,
                "generic_pct": 0.0,
                "generic_state": "ok",
                "b2_manager_sent_at": False,
                **vals,
            }
        )

    def test_b2_sends_one_email_per_department_and_marks_sent(self):
        rec1 = self._create_incident(employee=self.employee)
        rec2 = self._create_incident(
            employee=self.employee2
        )  # same dept/date, different employee

        with patch(
            "odoo.addons.mail.models.mail_template.MailTemplate.send_mail"
        ) as mocked_send:
            mocked_send.return_value = 1
            self.Compliance._cron_send_b2_manager_daily_emails()

        rec1.invalidate_recordset()
        rec2.invalidate_recordset()

        self.assertTrue(rec1.b2_manager_sent_at)
        self.assertTrue(rec2.b2_manager_sent_at)
        self.assertEqual(
            mocked_send.call_count,
            1,
            "B2 must send a single email per department/day",
        )

    def test_b2_is_idempotent_does_not_send_twice(self):
        rec = self._create_incident(employee=self.employee)

        with patch(
            "odoo.addons.mail.models.mail_template.MailTemplate.send_mail"
        ) as mocked_send:
            mocked_send.return_value = 1
            self.Compliance._cron_send_b2_manager_daily_emails()
            self.Compliance._cron_send_b2_manager_daily_emails()

        rec.invalidate_recordset()
        self.assertTrue(rec.b2_manager_sent_at)
        self.assertEqual(mocked_send.call_count, 1)

    def test_b2_does_not_send_without_manager_email(self):
        self.manager_user.email = False
        rec = self._create_incident(employee=self.employee)

        with patch(
            "odoo.addons.mail.models.mail_template.MailTemplate.send_mail"
        ) as mocked_send:
            mocked_send.return_value = 1
            self.Compliance._cron_send_b2_manager_daily_emails()

        rec.invalidate_recordset()
        self.assertFalse(
            rec.b2_manager_sent_at,
            "If no manager email, it must not mark as sent",
        )
        self.assertEqual(mocked_send.call_count, 0)
