# Copyright 2026 Moval
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date, timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests import tagged

from .common import TimesheetComplianceCase


@tagged("-at_install")
class TestComplianceE3WeeklyGenericQuality(TimesheetComplianceCase):
    def _make_user(self, login, email):
        user = self.env["res.users"].create(
            {
                "name": login,
                "login": login,
                "email": email,
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        return user

    def _make_employee(self, name, user, dept):
        return self.env["hr.employee"].create(
            {
                "name": name,
                "user_id": user.id,
                "department_id": dept.id,
                "company_id": user.company_id.id,
            }
        )

    def test_e3_weekly_sends_only_on_monday_and_builds_pivot_url(self):
        Compliance = self.env["timesheet.compliance"]

        manager_user = self._make_user("manager_e3", "manager_e3@example.com")
        dept = self.env["hr.department"].create(
            {
                "name": "Dept E3",
                "manager_id": self.env["hr.employee"]
                .create(
                    {
                        "name": "Dept Manager E3",
                        "user_id": manager_user.id,
                        "company_id": manager_user.company_id.id,
                    }
                )
                .id,
            }
        )

        emp_user = self._make_user("user_e3", "user_e3@example.com")
        employee = self._make_employee("Employee E3", emp_user, dept)

        # Pick a Monday as "today" so cron runs:
        monday = date(2026, 1, 12)  # Monday
        last_monday = monday - timedelta(days=monday.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)

        # Create compliance records for last week range
        d = last_monday
        while d <= last_sunday:
            Compliance.create(
                {
                    "employee_id": employee.id,
                    "date": fields.Date.to_string(d),
                    "telework": False,
                    "attendance_hours": 8.0,
                    "timesheet_hours": 8.0,
                    "delta_hours": 0.0,
                    "state": "ok",
                    "generic_hours": 2.0,
                    "generic_pct": 0.25,
                    "generic_state": "warn",
                }
            )
            d += timedelta(days=1)

        template = self.env.ref(
            "moval_timesheet_compliance.mail_template_timesheet_compliance_e3_weekly"
        )

        captured = {"calls": 0, "ctx": None}

        def _fake_send_mail(self, res_id, force_send=False, **kwargs):
            captured["calls"] += 1
            # Capture the render context used by with_context(...)
            captured["ctx"] = dict(self.env.context)
            return True

        # Patch context_today to be Monday, and patch send_mail to avoid real mail pipeline.
        with patch.object(
            fields.Date, "context_today", autospec=True, return_value=monday
        ):
            with patch.object(type(template), "send_mail", new=_fake_send_mail):
                Compliance._cron_send_e3_weekly_generic_quality()

        self.assertEqual(
            captured["calls"], 1, "E3 should send exactly one email for the department"
        )

        ctx = captured["ctx"] or {}
        self.assertEqual(ctx.get("department_name"), dept.display_name)
        self.assertEqual(ctx.get("date_from"), fields.Date.to_string(last_monday))
        self.assertEqual(ctx.get("date_to"), fields.Date.to_string(last_sunday))
        self.assertTrue(
            ctx.get("pivot_url"), "pivot_url should be present in template context"
        )
        self.assertIn("/web#", ctx.get("pivot_url"))

        # Now ensure it does NOT run on a non-Monday
        captured = {"calls": 0, "ctx": None}
        tuesday = monday + timedelta(days=1)
        with patch.object(
            fields.Date, "context_today", autospec=True, return_value=tuesday
        ):
            with patch.object(type(template), "send_mail", new=_fake_send_mail):
                Compliance._cron_send_e3_weekly_generic_quality()
        self.assertEqual(captured["calls"], 0, "E3 should not send on non-Monday")
