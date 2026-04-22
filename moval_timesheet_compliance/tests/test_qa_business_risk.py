# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0).
# pylint: disable=invalid-name,protected-access

"""High-value QA around real business and operational risk (not coverage bait)."""

import json
from datetime import datetime, time, timedelta
from unittest.mock import patch
from urllib.parse import unquote, urlparse

from odoo import fields
from odoo.fields import Date as OdooDate
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from .common import TimesheetComplianceCase, cleanup_employee_workday_for_tests


@tagged("post_install", "-at_install")
class TestComputeCronDateWindow(TransactionCase):
    """
    Nightly job must recompute a fixed rolling window: D-1 and D-2
    (no silent drift to other dates).
    """

    def test_cron_compute_compliance_requests_only_d_minus_1_and_d_minus_2(self):
        Compliance = self.env["timesheet.compliance"]
        model_cls = Compliance.__class__
        orig = model_cls.compute_for_dates
        captured = []
        today = fields.Date.from_string("2026-01-20")

        def _capture(self, dates, *args, **kwargs):
            captured.append([OdooDate.to_date(d) for d in (dates or [])])
            return orig(self, dates, *args, **kwargs)

        model_cls.compute_for_dates = _capture
        try:
            with patch("odoo.fields.Date.context_today", return_value=today):
                Compliance._cron_compute_compliance()
        finally:
            model_cls.compute_for_dates = orig

        self.assertEqual(
            len(captured),
            1,
            "compute_for_dates must be invoked once per cron run",
        )
        d1, d2 = sorted(captured[0])
        self.assertEqual(d1, today - timedelta(days=2))
        self.assertEqual(d2, today - timedelta(days=1))


@tagged("post_install", "-at_install")
class TestExcludedInclusionTogglesMonitoring(TransactionCase):
    """
    Exclusion is a control: clearing it must bring the employee back under batch compute.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.department = cls.env["hr.department"].create({"name": "Dept QAX"})
        cls.user = (
            cls.env["res.users"]
            .with_context(no_reset_password=True, mail_create_nosubscribe=True)
            .create(
                {
                    "name": "User QAX",
                    "login": "user_qax@example.com",
                    "email": "user_qax@example.com",
                    "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
                }
            )
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Employee QAX",
                "user_id": cls.user.id,
                "department_id": cls.department.id,
            }
        )
        cls.analytic_plan = cls.env["account.analytic.plan"].create(
            {"name": "Plan QAX"}
        )
        analytic_vals = {
            "name": "Analytic QAX",
            "company_id": cls.company.id,
        }
        if "plan_id" in cls.env["account.analytic.account"]._fields:
            analytic_vals["plan_id"] = cls.analytic_plan.id
        cls.aa = cls.env["account.analytic.account"].create(analytic_vals)
        cls.project = cls.env["project.project"].create(
            {
                "name": "Project QAX",
                "allow_timesheets": True,
                "analytic_account_id": cls.aa.id,
                "company_id": cls.company.id,
            }
        )
        cls.compliance = cls.env["timesheet.compliance"]
        cls.AAL = cls.env["account.analytic.line"]

    def _make_line(self, day, hours):
        vals = {
            "name": "QAX",
            "date": day,
            "unit_amount": hours,
            "project_id": self.project.id,
            "account_id": self.aa.id,
            "company_id": self.company.id,
        }
        if "employee_id" in self.AAL._fields:
            vals["employee_id"] = self.employee.id
        else:
            vals["user_id"] = self.user.id
        self.AAL.create(vals)

    def test_employee_included_again_receives_compliance_row_after_exclusion_lifts(
        self,
    ):
        day = fields.Date.from_string("2026-02-10")
        self.employee.x_timesheet_compliance_excluded = True
        self._make_line(day, 3.0)
        self.compliance.compute_for_dates([day])
        self.assertFalse(
            self.compliance.search(
                [("employee_id", "=", self.employee.id), ("date", "=", day)]
            )
        )
        self.employee.x_timesheet_compliance_excluded = False
        # More hours to avoid trivial edge cases; second compute updates same run
        self.compliance.compute_for_dates([day])
        rec = self.compliance.search(
            [("employee_id", "=", self.employee.id), ("date", "=", day)]
        )
        self.assertTrue(
            rec,
            "Lifting exclusion must make the employee part of the batch again",
        )
        self.assertGreaterEqual(
            rec.timesheet_hours,
            0.0,
        )


@tagged("post_install", "-at_install")
class TestJustifiedStatePreservesControlsRefreshMetrics(TransactionCase):
    """
    "Justified" is a business decision. Hours/generic risk signals must still refresh
    (payroll/audit), while workflow state is not auto-changed.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.x_generic_min_hours = 1.0
        cls.company.x_generic_warn_pct = 0.2
        cls.company.x_generic_issue_pct = 0.4
        cls.company.x_delta_tolerance_ok = 0.01
        cls.company.x_delta_warn_hours = 1.0
        cls.department = cls.env["hr.department"].create({"name": "Dept JUS"})

        cls.user = (
            cls.env["res.users"]
            .with_context(no_reset_password=True, mail_create_nosubscribe=True)
            .create(
                {
                    "name": "User JUS",
                    "login": "user_jus@example.com",
                    "email": "user_jus@example.com",
                    "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
                }
            )
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Employee JUS",
                "user_id": cls.user.id,
                "department_id": cls.department.id,
            }
        )
        cls.analytic_plan = cls.env["account.analytic.plan"].create(
            {"name": "Plan JUS"}
        )
        analytic_vals = {
            "name": "Analytic JUS",
            "company_id": cls.company.id,
        }
        if "plan_id" in cls.env["account.analytic.account"]._fields:
            analytic_vals["plan_id"] = cls.analytic_plan.id
        cls.aa = cls.env["account.analytic.account"].create(analytic_vals)
        cls.p_normal = cls.env["project.project"].create(
            {
                "name": "Normal JUS",
                "allow_timesheets": True,
                "analytic_account_id": cls.aa.id,
            }
        )
        cls.p_generic = cls.env["project.project"].create(
            {
                "name": "Generic JUS",
                "allow_timesheets": True,
                "analytic_account_id": cls.aa.id,
            }
        )
        cls.company.x_generic_project_ids = [(6, 0, [cls.p_generic.id])]
        cls.AAL = cls.env["account.analytic.line"]
        cls.Att = cls.env["hr.attendance"]
        cls.compliance = cls.env["timesheet.compliance"]

    def _line(self, day, hours, project):
        vals = {
            "name": "JUS",
            "date": day,
            "unit_amount": hours,
            "project_id": project.id,
            "account_id": project.analytic_account_id.id,
        }
        if "employee_id" in self.AAL._fields:
            vals["employee_id"] = self.employee.id
        else:
            vals["user_id"] = self.user.id
        return self.AAL.create(vals)

    def _att(self, day, h):
        start = datetime.combine(day, time(8, 0, 0))
        end = start + timedelta(hours=h)
        return self.Att.create(
            {
                "employee_id": self.employee.id,
                "check_in": start,
                "check_out": end,
            }
        )

    def test_justified_blocks_state_changes_but_stores_updated_generic_risk(self):
        day = fields.Date.from_string("2026-03-05")
        cleanup_employee_workday_for_tests(self.env, self.employee, day)
        # Create the justified record before timesheet lines: line creation can trigger
        # recompute that would already insert a (employee, date) compliance row.
        rec = self.compliance.create(
            {
                "employee_id": self.employee.id,
                "date": day,
                "state": "justified",
            }
        )
        self._att(day, 8.0)
        self._line(day, 7, self.p_generic)
        self._line(day, 1, self.p_normal)
        self.compliance.browse(rec.id).sudo()._compute_employee_date(self.employee, day)
        rec.invalidate_recordset()

        self.assertEqual(
            rec.state, "justified", "A manual justification must survive recompute"
        )
        self.assertAlmostEqual(rec.timesheet_hours, 8.0, places=2)
        self.assertEqual(
            rec.generic_state,
            "issue",
            "7/8 generic share must still surface as issue in metrics under justification",
        )


@tagged("post_install", "-at_install")
class TestB1EmailRendersInNonDefaultLanguage(TimesheetComplianceCase):
    """
    B1 is sent to real people: a missing translation file must not crash the render
    (English fallback is fine in production, server errors are not).
    """

    def test_b1_template_renders_without_error_when_employee_user_lang_is_not_english(
        self,
    ):
        if not self.env["res.lang"].search([("code", "=", "es_ES")], limit=1):
            self.env["res.lang"]._activate_lang("es_ES")
        user = (
            self.env["res.users"]
            .with_context(no_reset_password=True, mail_create_nosubscribe=True)
            .create(
                {
                    "name": "User Lang B1",
                    "login": "user_lang_b1",
                    "email": "user_lang@example.com",
                    "lang": "es_ES",
                    "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
                }
            )
        )
        employee = self.env["hr.employee"].create(
            {
                "name": "Emp Lang B1",
                "user_id": user.id,
                "company_id": self.env.company.id,
            }
        )
        day = fields.Date.from_string("2026-01-10")
        compliance = self.env["timesheet.compliance"].create(
            {
                "employee_id": employee.id,
                "date": day,
                "telework": True,
                "attendance_hours": 8.0,
                "timesheet_hours": 7.0,
                "delta_hours": 1.0,
                "state": "warn",
                "generic_hours": 0.0,
                "generic_pct": 0.0,
            }
        )
        template = self.env.ref(
            "moval_timesheet_compliance.mail_template_timesheet_compliance_daily"
        )
        ctx = compliance._get_b1_email_render_context()
        m = template.with_context(**ctx, lang=employee.user_id.lang)._render_template(
            template.body_html, template.model, [compliance.id]
        )
        html = m.get(compliance.id) or ""
        self.assertTrue(len(html) > 50)
        self.assertNotIn("Traceback", html)


@tagged("post_install", "-at_install")
class TestB2ManagerDepartmentActionDomain(TransactionCase):
    """
    B2 "open all lines" must stay department-scoped (leaking other org units is
    a confidentiality risk).
    """

    def test_b2_department_timesheet_url_domain_binds_employees_in_department(self):
        dept = self.env["hr.department"].create({"name": "Dept B2B"})
        u1 = (
            self.env["res.users"]
            .with_context(no_reset_password=True, mail_create_nosubscribe=True)
            .create(
                {
                    "name": "U1 B2B",
                    "login": "u1_b2b@example.com",
                    "email": "u1_b2b@example.com",
                    "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
                }
            )
        )
        u2 = (
            self.env["res.users"]
            .with_context(no_reset_password=True, mail_create_nosubscribe=True)
            .create(
                {
                    "name": "U2 B2B",
                    "login": "u2_b2b@example.com",
                    "email": "u2_b2b@example.com",
                    "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
                }
            )
        )
        e1 = self.env["hr.employee"].create(
            {"name": "E1 B2B", "user_id": u1.id, "department_id": dept.id}
        )
        e2 = self.env["hr.employee"].create(
            {"name": "E2 B2B", "user_id": u2.id, "department_id": dept.id}
        )
        d = fields.Date.from_string("2026-01-10")
        url = self.env["timesheet.compliance"]._get_b2_department_action_url(dept, d)
        if not url:
            self.skipTest("web.base.url is not set in the test environment")
        self.assertTrue(url, "A department manager must get a real drill-down URL")
        # Parse domain from /web#hash
        h = urlparse(url).fragment
        for part in h.split("&"):
            if part.startswith("domain="):
                dom = json.loads(unquote(part.split("=", 1)[1]))
                # Expect employee filter; exact shape depends on hr_timesheet aal fields
                djson = str(dom)
                if "employee_id" in self.env["account.analytic.line"]._fields:
                    self.assertIn("employee_id", djson)
                    for xid in (e1.id, e2.id):
                        self.assertIn(str(xid), djson)
                else:
                    # user_id fallback: still a bounded in-list
                    self.assertIn("user_id", djson)
                return
        self.fail("No domain= parameter in manager drill-down URL")


@tagged("post_install", "-at_install")
class TestB2ManagerTemplateTranslationSafe(TimesheetComplianceCase):
    """B2 is manager-facing: rendering must be robust for non-English UIs."""

    def test_b2_manager_body_renders_without_error_under_spanish_lang(self):
        if not self.env["res.lang"].search([("code", "=", "es_ES")], limit=1):
            self.env["res.lang"]._activate_lang("es_ES")
        user = (
            self.env["res.users"]
            .with_context(no_reset_password=True, mail_create_nosubscribe=True)
            .create(
                {
                    "name": "User B2L",
                    "login": "user_b2l@example.com",
                    "email": "user_b2l@example.com",
                    "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
                }
            )
        )
        dept = self.env["hr.department"].create({"name": "Dept B2L"})
        employee = self.env["hr.employee"].create(
            {
                "name": "Emp B2L",
                "user_id": user.id,
                "department_id": dept.id,
            }
        )
        day = fields.Date.from_string("2026-01-10")
        compliance = self.env["timesheet.compliance"].create(
            {
                "employee_id": employee.id,
                "date": day,
                "state": "ok",
            }
        )
        template = self.env.ref(
            "moval_timesheet_compliance.mail_template_timesheet_compliance_b2_manager"
        )
        ctx = {
            "department_name": "QA Dept",
            "target_date": str(day),
            "incident_rows": [],
            "email_to_override": "mgr@example.com",
        }
        m = template.with_context(**ctx, lang="es_ES")._render_template(
            template.body_html, template.model, [compliance.id]
        )
        html = m.get(compliance.id) or ""
        self.assertIn(b"<div", html.encode("utf-8"))
        self.assertNotIn("Traceback", html)
