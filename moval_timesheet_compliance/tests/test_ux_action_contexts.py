# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0).
# pylint: disable=invalid-name,protected-access

from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from .common import TimesheetComplianceCase


@tagged("post_install", "-at_install")
class TestUxActionContexts(TimesheetComplianceCase):
    def test_moval_action_merge_context_dict(self):
        """Merging into dict context leaves previous keys and adds new ones."""
        m = self.env["timesheet.compliance"]
        base = {"id": 1, "name": "x", "context": {"a": 1, "b": 2}}
        m._moval_action_merge_context(base, b=3, c=4)
        self.assertEqual(
            base["context"],
            {"a": 1, "b": 3, "c": 4},
        )

    def test_moval_action_merge_context_string(self):
        """Merging into string context (literal) produces updated dict on action."""
        m = self.env["timesheet.compliance"]
        base = {"id": 1, "name": "x", "context": "{'foo': 1}"}
        m._moval_action_merge_context(base, search_default_x=1)
        self.assertEqual(base["context"], {"foo": 1, "search_default_x": 1})

    def test_action_open_compliance_today_domain_and_name(self):
        today = fields.Date.context_today(self.env.user)
        m = self.env["timesheet.compliance"]
        act = m.action_open_compliance_today()
        self.assertIn("name", act)
        self.assertEqual(
            act["name"],
            "Timesheet compliance: today",
        )
        self.assertEqual(act["domain"], [("date", "=", today)])
        self.assertIsInstance(act.get("context"), dict)

    def test_action_open_daily_compliance_yesterday_today(self):
        today = fields.Date.context_today(self.env.user)
        yesterday = today - timedelta(days=1)
        act = self.env["timesheet.compliance"].action_open_daily_compliance()
        self.assertEqual(
            act["name"],
            "Timesheet compliance: last 2 days",
        )
        self.assertIn(("date", ">=", yesterday), act["domain"])
        self.assertIn(("date", "<=", today), act["domain"])

    def test_action_open_analysis_today_merges_pivot_context(self):
        m = self.env["timesheet.compliance"]
        act = m.action_open_analysis_today()
        today = fields.Date.context_today(m.env.user)
        self.assertEqual(act.get("res_model"), "timesheet.compliance")
        self.assertIn("pivot", act.get("view_mode", ""))
        self.assertEqual(act.get("domain"), [("date", "=", today)])
        ctx = act.get("context") or {}
        self.assertEqual(ctx.get("search_default_groupby_dept"), 1)
        self.assertEqual(ctx.get("search_default_compliance_date"), 1)
        self.assertEqual(ctx.get("search_default_groupby_date"), 1)

    def test_compliance_pivot_url_uses_employee_groupby(self):
        """E-mail / weekly pivot deep link keeps group-by keys matching search filters."""
        m = self.env["timesheet.compliance"]
        dept = self.env["hr.department"].search([], limit=1)
        if not dept:
            self.skipTest("No department in DB for pivot URL test")
        d0 = fields.Date.context_today(m.env.user)
        d1 = d0
        url = m._get_compliance_pivot_url(dept, d0, d1)
        if not url:
            self.skipTest("No base URL configured")
        self.assertIn("search_default_groupby_emp", url)
        self.assertIn("search_default_groupby_date", url)
