# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# pylint: disable=invalid-name,protected-access

from datetime import datetime, time, timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests.common import TransactionCase

from .common import cleanup_employee_workday_for_tests, skip_compliance_recompute_on


class TestComplianceExcludedProjects(TransactionCase):
    """`company_id.x_compliance_excluded_project_ids` without code changes."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.x_generic_min_hours = 1.0
        cls.company.x_generic_warn_pct = 0.20
        cls.company.x_generic_issue_pct = 0.40
        cls.company.x_delta_tolerance_ok = 0.01
        cls.company.x_delta_warn_hours = 0.5

        cls.department = cls.env["hr.department"].create({"name": "Dept A5"})

        cls.user = (
            cls.env["res.users"]
            .with_context(no_reset_password=True, mail_create_nosubscribe=True)
            .create(
                {
                    "name": "User A5",
                    "login": "user_a5@example.com",
                    "email": "user_a5@example.com",
                    "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
                }
            )
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Employee A5",
                "user_id": cls.user.id,
                "department_id": cls.department.id,
                "company_id": cls.company.id,
            }
        )

        cls.analytic_plan = cls.env["account.analytic.plan"].create({"name": "Plan A5"})
        analytic_vals = {"name": "Analytic A5", "company_id": cls.company.id}
        if "plan_id" in cls.env["account.analytic.account"]._fields:
            analytic_vals["plan_id"] = cls.analytic_plan.id
        cls.analytic_account = cls.env["account.analytic.account"].create(analytic_vals)

        cls.project_normal = cls.env["project.project"].create(
            {
                "name": "Project Normal A5",
                "allow_timesheets": True,
                "analytic_account_id": cls.analytic_account.id,
                "company_id": cls.company.id,
            }
        )
        cls.project_internal_absence = cls.env["project.project"].create(
            {
                "name": "Internal absence A5",
                "allow_timesheets": True,
                "analytic_account_id": cls.analytic_account.id,
                "company_id": cls.company.id,
            }
        )
        cls.project_generic = cls.env["project.project"].create(
            {
                "name": "Project Generic A5",
                "allow_timesheets": True,
                "analytic_account_id": cls.analytic_account.id,
                "company_id": cls.company.id,
            }
        )
        cls.company.x_generic_project_ids = [(6, 0, [cls.project_generic.id])]
        # Ensure clean exclusion list; tests set projects explicitly.
        cls.company.x_compliance_excluded_project_ids = [(5, 0, 0)]

        cls.Compliance = cls.env["timesheet.compliance"]
        cls.AAL = cls.env["account.analytic.line"]
        cls.Att = cls.env["hr.attendance"]

    def _make_attendance(self, day, hours, env=None):
        e = (env or self.env)["hr.attendance"]
        start_dt = datetime.combine(day, time(8, 0, 0))
        end_dt = start_dt + timedelta(hours=hours)
        e.create(
            {
                "employee_id": self.employee.id,
                "check_in": start_dt,
                "check_out": end_dt,
            }
        )

    def _make_timesheet(self, day, hours, project, env=None):
        AAL = (env or self.env)["account.analytic.line"]
        vals = {
            "name": "TS",
            "date": day,
            "unit_amount": hours,
            "project_id": project.id,
            "account_id": project.analytic_account_id.id,
            "company_id": self.company.id,
        }
        if "employee_id" in AAL._fields:
            vals["employee_id"] = self.employee.id
        else:
            vals["user_id"] = self.user.id
        return AAL.create(vals)

    def test_a5_exclusion_configuration_triggers_different_recompute(self):
        """Excluding a project is configurable; the next recompute must apply it."""
        fixed_today = fields.Date.from_string("2099-02-02")
        d = fixed_today - timedelta(days=1)
        cleanup_employee_workday_for_tests(self.env, self.employee, d)
        with skip_compliance_recompute_on(self.env) as e:
            self._make_attendance(d, 8.0, env=e)
            self._make_timesheet(d, 2.0, self.project_internal_absence, env=e)
            self._make_timesheet(d, 6.0, self.project_normal, env=e)

        with patch("odoo.fields.Date.context_today", return_value=fixed_today):
            self.Compliance.with_company(self.company).sudo()._compute_employee_date(
                self.employee, d
            )

        rec = self.Compliance.search(
            [("employee_id", "=", self.employee.id), ("date", "=", d)], limit=1
        )
        self.assertTrue(rec)
        self.assertAlmostEqual(rec.timesheet_hours, 8.0, places=2, msg="all projects")
        self.assertEqual(rec.state, "ok", msg="8h att vs 8h ts = ok")

        self.company.x_compliance_excluded_project_ids = [
            (6, 0, [self.project_internal_absence.id])
        ]
        with patch("odoo.fields.Date.context_today", return_value=fixed_today):
            self.Compliance.with_company(self.company).sudo()._compute_employee_date(
                self.employee, d
            )

        rec.invalidate_recordset()
        self.assertAlmostEqual(
            rec.timesheet_hours, 6.0, places=2, msg="exclude 2h absence"
        )
        self.assertAlmostEqual(rec.attendance_hours, 8.0, places=2)
        self.assertEqual(rec.state, "issue", msg="delta 2h above warn threshold 0.5h")

    def test_a5_generic_ignores_excluded_even_if_also_marked_generic(self):
        """Compliance-excluded generic projects do not add to generic quality hours."""
        fixed_today = fields.Date.from_string("2026-02-03")
        d = fixed_today - timedelta(days=1)
        # Generic project is both generic and later compliance-excluded.
        self.company.x_compliance_excluded_project_ids = [
            (6, 0, [self.project_generic.id])
        ]
        self._make_attendance(d, 4.0)
        self._make_timesheet(d, 2.0, self.project_generic)
        self._make_timesheet(d, 2.0, self.project_normal)

        with patch("odoo.fields.Date.context_today", return_value=fixed_today):
            self.Compliance._cron_compute_compliance()

        rec = self.Compliance.search(
            [("employee_id", "=", self.employee.id), ("date", "=", d)], limit=1
        )
        self.assertTrue(rec)
        self.assertAlmostEqual(rec.timesheet_hours, 2.0, places=2)
        self.assertAlmostEqual(rec.generic_hours, 0.0, places=2)
        self.assertEqual(
            rec.generic_state,
            "ok",
            msg="no generic count when the only generic project is excluded",
        )

    def test_a5_email_breakdowns_skip_excluded_projects(self):
        """B1 project breakdown must not list hours on compliance-excluded projects."""
        d = fields.Date.from_string("2026-02-10")
        self.company.x_compliance_excluded_project_ids = [
            (6, 0, [self.project_internal_absence.id])
        ]
        self._make_timesheet(d, 1.0, self.project_internal_absence)
        self._make_timesheet(d, 5.0, self.project_normal)
        self.Compliance._compute_employee_date(self.employee, d)
        rec = self.Compliance.search(
            [("employee_id", "=", self.employee.id), ("date", "=", d)], limit=1
        )
        self.assertTrue(rec)
        projects = {r["project_name"] for r in rec._get_project_hours_breakdown()}
        self.assertIn(self.project_normal.name, projects)
        self.assertNotIn(
            self.project_internal_absence.name,
            projects,
            "Excluded project must not appear in breakdown",
        )
