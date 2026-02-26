# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# pylint: disable=invalid-name,protected-access

from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests.common import TransactionCase


class TestComplianceDailyB1(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.Compliance = cls.env["timesheet.compliance"]
        cls.Employee = cls.env["hr.employee"]
        cls.Users = cls.env["res.users"]

        cls.today = fields.Date.context_today(cls.env.user)
        cls.target_date = cls.today - timedelta(days=1)

        cls.template = cls.env.ref(
            "moval_timesheet_compliance.mail_template_timesheet_compliance_daily",
            raise_if_not_found=False,
        )
        assert cls.template, "Missing B1 mail template XML ID"

    def setUp(self):
        super().setUp()
        now = fields.Datetime.now()
        self.Compliance.search([("date", "=", self.target_date)]).write(
            {"email_sent_at": now}
        )

    def _create_employee_with_user(self, login, email):
        user = self.Users.with_context(
            no_reset_password=True, mail_create_nosubscribe=True
        ).create(
            {
                "name": login,
                "login": login,
                "email": email,
            }
        )
        employee = self.Employee.create(
            {
                "name": f"Emp {login}",
                "user_id": user.id,
            }
        )
        return employee

    def _create_compliance(self, employee, **vals):
        values = {
            "employee_id": employee.id,
            "date": self.target_date,
            "email_sent_at": False,
            "telework": False,
            "state": "ok",
            "attendance_hours": 0.0,
            "timesheet_hours": 0.0,
            "delta_hours": 0.0,
        }
        values.update(vals)
        return self.Compliance.create(values)

    def _patch_send_mail(self):
        return patch.object(
            type(self.env["mail.template"]),
            "send_mail",
            autospec=True,
        )

    def test_b1_does_not_send_when_ok_and_not_telework(self):
        employee = self._create_employee_with_user(
            "user_b1_ok", "user_b1_ok@example.com"
        )
        self._create_compliance(employee, state="ok", telework=False)

        with self._patch_send_mail() as mocked_send:
            self.Compliance._cron_send_b1_employee_daily_emails()
            self.assertEqual(mocked_send.call_count, 0)

    def test_b1_sends_when_state_warn_or_issue(self):
        employee = self._create_employee_with_user(
            "user_b1_warn", "user_b1_warn@example.com"
        )
        rec = self._create_compliance(employee, state="warn", telework=False)

        with self._patch_send_mail() as mocked_send:
            self.Compliance._cron_send_b1_employee_daily_emails()
            self.assertEqual(mocked_send.call_count, 1)

        self.assertTrue(rec.email_sent_at)

    def test_b1_sends_when_telework_true(self):
        employee = self._create_employee_with_user(
            "user_b1_tw", "user_b1_tw@example.com"
        )
        rec = self._create_compliance(employee, state="ok", telework=True)

        with self._patch_send_mail() as mocked_send:
            self.Compliance._cron_send_b1_employee_daily_emails()
            self.assertEqual(mocked_send.call_count, 1)

        self.assertTrue(rec.email_sent_at)

    def test_b1_is_idempotent_does_not_send_twice(self):
        employee = self._create_employee_with_user(
            "user_b1_once", "user_b1_once@example.com"
        )
        self._create_compliance(employee, state="warn", telework=False)

        with self._patch_send_mail() as mocked_send:
            self.Compliance._cron_send_b1_employee_daily_emails()
            self.assertEqual(mocked_send.call_count, 1)

            self.Compliance._cron_send_b1_employee_daily_emails()
            self.assertEqual(mocked_send.call_count, 1)

    def test_b1_does_not_send_when_employee_excluded(self):
        employee = self._create_employee_with_user(
            "user_b1_excluded", "user_b1_excluded@example.com"
        )
        employee.x_timesheet_compliance_excluded = True
        self._create_compliance(employee, state="warn", telework=False)

        with self._patch_send_mail() as mocked_send:
            self.Compliance._cron_send_b1_employee_daily_emails()
            self.assertEqual(mocked_send.call_count, 0)
