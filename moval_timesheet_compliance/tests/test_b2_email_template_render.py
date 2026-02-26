# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# pylint: disable=invalid-name,protected-access

from datetime import timedelta

from odoo import fields
from odoo.tests import tagged
from odoo.tools.misc import mute_logger

from .common import TimesheetComplianceCase


@tagged("post_install", "-at_install")
@mute_logger("odoo.addons.auth_signup.models.res_users")
class TestComplianceDailyB2(TimesheetComplianceCase):
    TEMPLATE_XMLID = (
        "moval_timesheet_compliance.mail_template_timesheet_compliance_daily"
    )
    ACTION_XMLID = "moval_timesheet_compliance.action_moval_my_timesheets_by_date"

    def test_b2_template_renders_and_contains_link(self):
        template = self.env.ref(self.TEMPLATE_XMLID)

        user = self.env.ref("base.user_demo")
        user.email = user.email or "user_b2@example.com"

        employee = self.env["hr.employee"].create(
            {
                "name": "Employee B2",
                "user_id": user.id,
                "company_id": user.company_id.id,
            }
        )

        day = fields.Date.context_today(self.env.user) - timedelta(days=1)
        compliance = self.env["timesheet.compliance"].create(
            {
                "employee_id": employee.id,
                "date": day,
                "telework": True,
                "attendance_hours": 8.0,
                "timesheet_hours": 7.0,
                "delta_hours": 1.0,
                "state": "warn",
                "generic_hours": 2.0,
                "generic_pct": 2.0 / 7.0,
                "generic_state": "warn",
            }
        )

        rendered_map = template.with_context(
            **compliance._get_b1_email_render_context()
        )._render_template(template.body_html, template.model, [compliance.id])

        rendered = rendered_map.get(compliance.id) or ""
        self.assertTrue(rendered)

        subject_map = template._render_template(
            template.subject or "", template.model, [compliance.id]
        )
        subject = subject_map.get(compliance.id) or ""
        self.assertTrue(subject)

        action = self.env.ref(self.ACTION_XMLID)
        self.assertIn(str(action.id), rendered)
        self.assertIn("my_timesheets_url", template.body_html)

        self.assertIn(str(day), rendered)
        self.assertIn("Telework", rendered)
        self.assertIn("Attendance", rendered)
        self.assertIn("Timesheet", rendered)
        self.assertIn("Delta", rendered)
        self.assertIn("Generic", rendered)
        self.assertIn("Open “My timesheets for this day”", rendered)
        self.assertIn('href="', rendered)
        self.assertIn("/web", rendered)
        self.assertIn("/web#action=", rendered)
        self.assertIn("moval_timesheet_date", rendered)
