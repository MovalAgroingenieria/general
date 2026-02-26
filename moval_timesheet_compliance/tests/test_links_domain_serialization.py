# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# pylint: disable=invalid-name,protected-access

from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from .common import TimesheetComplianceCase


@tagged("post_install", "-at_install")
class TestComplianceLinks(TimesheetComplianceCase):
    def test_b2_employee_day_url_serializes_date(self):
        user = (
            self.env["res.users"]
            .with_context(no_reset_password=True, mail_create_nosubscribe=True)
            .create(
                {
                    "name": "Link Test User",
                    "login": "link_test_user",
                    "email": "link_test_user@example.com",
                    "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
                }
            )
        )
        employee = self.env["hr.employee"].create(
            {
                "name": "Employee Link",
                "user_id": user.id,
                "company_id": user.company_id.id,
            }
        )

        day = fields.Date.context_today(self.env.user) - timedelta(days=1)
        rec = self.env["timesheet.compliance"].create(
            {
                "employee_id": employee.id,
                "date": day,
                "telework": False,
                "attendance_hours": 8.0,
                "timesheet_hours": 8.0,
                "delta_hours": 0.0,
                "state": "ok",
            }
        )

        url = rec._get_b2_employee_day_url()
        self.assertTrue(url)
        self.assertIn("/web#model=account.analytic.line", url)
        self.assertIn("&domain=", url)

    def test_action_open_timesheets_returns_correct_domain(self):
        """action_open_timesheets returns act_window domain for employee+date."""
        user = (
            self.env["res.users"]
            .with_context(no_reset_password=True, mail_create_nosubscribe=True)
            .create(
                {
                    "name": "Action Test User",
                    "login": "action_test_user",
                    "email": "action_test@example.com",
                    "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
                }
            )
        )
        employee = self.env["hr.employee"].create(
            {"name": "Employee Action", "user_id": user.id}
        )
        day = fields.Date.context_today(self.env.user) - timedelta(days=1)
        rec = self.env["timesheet.compliance"].create(
            {
                "employee_id": employee.id,
                "date": day,
                "state": "ok",
                "attendance_hours": 8.0,
                "timesheet_hours": 8.0,
                "delta_hours": 0.0,
            }
        )

        action = rec.action_open_timesheets()
        self.assertEqual(action["res_model"], "account.analytic.line")
        self.assertEqual(action["view_mode"], "tree,form")
        self.assertIn("domain", action)
        self.assertIn(("date", "=", day), action["domain"])
        self.assertIn("default_date", action["context"])
        self.assertEqual(action["context"]["default_date"], day)

    def test_action_open_attendances_returns_correct_domain(self):
        """action_open_attendances returns act_window domain for employee+date."""
        user = (
            self.env["res.users"]
            .with_context(no_reset_password=True, mail_create_nosubscribe=True)
            .create(
                {
                    "name": "Action Att User",
                    "login": "action_att_user",
                    "email": "action_att@example.com",
                    "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
                }
            )
        )
        employee = self.env["hr.employee"].create(
            {"name": "Employee Att", "user_id": user.id}
        )
        day = fields.Date.context_today(self.env.user) - timedelta(days=1)
        rec = self.env["timesheet.compliance"].create(
            {
                "employee_id": employee.id,
                "date": day,
                "state": "ok",
                "attendance_hours": 8.0,
                "timesheet_hours": 8.0,
                "delta_hours": 0.0,
            }
        )

        action = rec.action_open_attendances()
        self.assertEqual(action["res_model"], "hr.attendance")
        self.assertEqual(action["view_mode"], "tree,form")
        self.assertIn("domain", action)
        self.assertEqual(action["domain"].count(("employee_id", "=", employee.id)), 1)
        self.assertIn("default_employee_id", action["context"])
        self.assertEqual(action["context"]["default_employee_id"], employee.id)

    def test_action_mark_justified(self):
        """action_mark_justified sets state to justified."""
        user = (
            self.env["res.users"]
            .with_context(no_reset_password=True, mail_create_nosubscribe=True)
            .create(
                {
                    "name": "Justified User",
                    "login": "justified_user",
                    "email": "justified@example.com",
                    "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
                }
            )
        )
        employee = self.env["hr.employee"].create(
            {"name": "Employee Just", "user_id": user.id}
        )
        day = fields.Date.context_today(self.env.user) - timedelta(days=1)
        rec = self.env["timesheet.compliance"].create(
            {
                "employee_id": employee.id,
                "date": day,
                "state": "warn",
                "attendance_hours": 8.0,
                "timesheet_hours": 6.0,
                "delta_hours": 2.0,
            }
        )

        rec.action_mark_justified()
        self.assertEqual(rec.state, "justified")
