# Copyright 2026 Moval
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from .common import TimesheetComplianceCase


@tagged("post_install", "-at_install")
class TestComplianceLinks(TimesheetComplianceCase):
    def test_b2_employee_day_url_serializes_date(self):
        user = self.env["res.users"].create(
            {
                "name": "Link Test User",
                "login": "link_test_user",
                "email": "link_test_user@example.com",
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
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
