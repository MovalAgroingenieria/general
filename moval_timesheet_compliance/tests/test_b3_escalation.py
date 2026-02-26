# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# pylint: disable=invalid-name,protected-access

from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests import tagged

from .common import TimesheetComplianceCase


@tagged("-at_install")
class TestComplianceDailyB3Escalation(TimesheetComplianceCase):
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

        cls.today = fields.Date.context_today(cls.env.user)
        cls.old_date = cls.today - timedelta(days=12)
        cls.old_date2 = cls.today - timedelta(days=47)

        # Manager setup (department manager gets escalation email)
        cls.manager_user = cls.Users.with_context(
            no_reset_password=True, mail_create_nosubscribe=True
        ).create(
            {
                "name": "Manager B3",
                "login": "manager_b3",
                "email": "manager_b3@example.com",
                "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.manager_employee = cls.Employees.create(
            {
                "name": "Manager Employee B3",
                "user_id": cls.manager_user.id,
            }
        )
        cls.department = cls.Department.create(
            {
                "name": "Department B3",
                "manager_id": cls.manager_employee.id,
            }
        )

        # Employee to escalate
        cls.user = cls.Users.with_context(
            no_reset_password=True, mail_create_nosubscribe=True
        ).create(
            {
                "name": "User B3",
                "login": "user_b3",
                "email": "user_b3@example.com",
                "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.employee = cls.Employees.create(
            {
                "name": "Employee B3",
                "user_id": cls.user.id,
                "department_id": cls.department.id,
            }
        )

    def _create_unresolved(self, date=False, **vals):
        if not date:
            date = self.old_date
        return self.Compliance.create(
            {
                "employee_id": self.employee.id,
                "department_id": self.department.id,
                "date": date,
                "telework": False,
                "state": "warn",
                "attendance_hours": 18.0,
                "timesheet_hours": 16.0,
                "delta_hours": 2.0,
                "generic_hours": 0.0,
                "generic_pct": 0.0,
                "generic_state": "ok",
                "escalated_at": False,
                **vals,
            }
        )

    def test_b3_escalates_and_marks_datetime_and_sends_email(self):
        rec = self._create_unresolved(state="warn")

        with patch(
            "odoo.addons.mail.models.mail_template.MailTemplate.send_mail"
        ) as mocked_send:
            mocked_send.return_value = 1
            self.Compliance._cron_send_b3_escalate_unresolved()

        rec.invalidate_recordset()
        self.assertEqual(rec.state, "escalated")
        self.assertTrue(rec.escalated_at)
        self.assertEqual(mocked_send.call_count, 1)

    def test_b3_is_idempotent_does_not_escalate_twice(self):
        rec = self._create_unresolved(state="issue")

        with patch(
            "odoo.addons.mail.models.mail_template.MailTemplate.send_mail"
        ) as mocked_send:
            mocked_send.return_value = 1
            self.Compliance._cron_send_b3_escalate_unresolved()
            self.Compliance._cron_send_b3_escalate_unresolved()

        rec.invalidate_recordset()
        self.assertEqual(rec.state, "escalated")
        self.assertTrue(rec.escalated_at)
        self.assertEqual(mocked_send.call_count, 1)

    def test_b3_does_not_touch_already_escalated(self):
        rec = self._create_unresolved(state="warn", escalated_at=fields.Datetime.now())

        with patch(
            "odoo.addons.mail.models.mail_template.MailTemplate.send_mail"
        ) as mocked_send:
            mocked_send.return_value = 1
            self.Compliance._cron_send_b3_escalate_unresolved()

        rec.invalidate_recordset()
        self.assertEqual(rec.state, "warn", "If escalated_at is set, cron must skip it")
        self.assertEqual(mocked_send.call_count, 0)

    def test_b3_does_not_escalate_fixed_or_justified(self):
        rec_fixed = self._create_unresolved(state="fixed", date=self.old_date)
        rec_just = self._create_unresolved(state="justified", date=self.old_date2)

        with patch(
            "odoo.addons.mail.models.mail_template.MailTemplate.send_mail"
        ) as mocked_send:
            mocked_send.return_value = 1
            self.Compliance._cron_send_b3_escalate_unresolved()

        rec_fixed.invalidate_recordset()
        rec_just.invalidate_recordset()

        self.assertFalse(rec_fixed.escalated_at)
        self.assertFalse(rec_just.escalated_at)
        self.assertEqual(mocked_send.call_count, 0)

    def test_b3_does_not_escalate_excluded_employee(self):
        """B3 cron must not escalate compliances of excluded employees."""
        self.employee.x_timesheet_compliance_excluded = True
        rec = self._create_unresolved(state="warn")

        with patch(
            "odoo.addons.mail.models.mail_template.MailTemplate.send_mail"
        ) as mocked_send:
            self.Compliance._cron_send_b3_escalate_unresolved()

        rec.invalidate_recordset()
        self.assertFalse(
            rec.escalated_at,
            "Excluded employee must not be escalated",
        )
        self.assertEqual(rec.state, "warn")
        self.assertEqual(mocked_send.call_count, 0)
