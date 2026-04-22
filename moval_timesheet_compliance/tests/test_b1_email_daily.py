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

    def _create_employee_user_no_email(self, login):
        user = self.Users.with_context(
            no_reset_password=True, mail_create_nosubscribe=True
        ).create(
            {
                "name": login,
                "login": login,
            }
        )
        return self.Employee.create(
            {
                "name": f"Emp {login}",
                "user_id": user.id,
            }
        )

    def test_b1_no_send_cron_and_action_when_user_email_missing(self):
        """Cron domain excludes; direct action logs skip, does not mark sent."""
        employee = self._create_employee_user_no_email("user_b1_noe")
        rec = self._create_compliance(employee, state="warn", telework=False)
        with self._patch_send_mail() as mocked_send:
            self.Compliance._cron_send_b1_employee_daily_emails()
            self.assertEqual(mocked_send.call_count, 0)
        res = rec.action_send_b1_employee_email()
        self.assertFalse(res)
        self.assertFalse(rec.email_sent_at)
        rec.invalidate_recordset()
        self.assertIn("Skipped", rec.b1_last_log or "")

    def test_b1_tech_log_and_chatter_on_success(self):
        employee = self._create_employee_with_user(
            "user_b1_ch", "user_b1_ch@example.com"
        )
        rec = self._create_compliance(employee, state="issue", telework=False)
        with self._patch_send_mail():
            self.Compliance._cron_send_b1_employee_daily_emails()
        rec.invalidate_recordset()
        self.assertTrue(rec.email_sent_at)
        self.assertIn("Sent to", rec.b1_last_log or "")
        self.assertIn("user_b1_ch@example.com", rec.b1_last_log)
        self.assertTrue(
            self.env["mail.message"].search_count(
                [
                    ("model", "=", "timesheet.compliance"),
                    ("res_id", "=", rec.id),
                ]
            )
        )

    def test_b1_send_error_logs_and_chatter(self):
        employee = self._create_employee_with_user(
            "user_b1_err", "user_b1_err@example.com"
        )
        rec = self._create_compliance(employee, state="warn", telework=False)
        with patch.object(
            type(self.env["mail.template"]),
            "send_mail",
            side_effect=RuntimeError("test smtp error"),
        ):
            res = rec.action_send_b1_employee_email()
        self.assertFalse(res)
        rec.invalidate_recordset()
        self.assertFalse(rec.email_sent_at)
        self.assertIn("Failed", rec.b1_last_log or "")
        self.assertIn(
            "B1: sending failed",
            "".join(
                m.body or ""
                for m in self.env["mail.message"].search(
                    [("model", "=", "timesheet.compliance"), ("res_id", "=", rec.id)]
                )
            ),
        )

    def test_b1_cron_idempotent_does_not_duplicate_tech_log_lines(self):
        """Second cron: no new send, no new duplicate Sent log (early exit)."""
        employee = self._create_employee_with_user(
            "user_b1_idemlog", "user_b1_idemlog@example.com"
        )
        self._create_compliance(employee, state="warn", telework=False)
        with self._patch_send_mail():
            self.Compliance._cron_send_b1_employee_daily_emails()
        first = self.Compliance.search(
            [
                ("employee_id", "=", employee.id),
                ("date", "=", self.target_date),
            ],
            limit=1,
        )
        log1 = first.b1_last_log
        t1 = first.b1_last_log_at
        with self._patch_send_mail() as mocked:
            self.Compliance._cron_send_b1_employee_daily_emails()
        first.invalidate_recordset()
        self.assertEqual(mocked.call_count, 0)
        self.assertEqual(first.b1_last_log, log1)
        self.assertEqual(first.b1_last_log_at, t1)

    def test_b1_debug_cron_info_matches_domain(self):
        self._create_employee_with_user("user_b1_dbg", "user_b1_dbg@example.com")
        # ensure one new compliance
        e = self.Employee.search([("user_id.login", "=", "user_b1_dbg")], limit=1)
        self._create_compliance(e, state="warn", telework=False)
        info = self.Compliance._b1_debug_cron_info(self.target_date)
        self.assertEqual(info["target_date"], str(self.target_date))
        self.assertGreaterEqual(info["count"], 1)
        self.assertTrue(info["ids"])
