# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# pylint: disable=invalid-name,protected-access

from datetime import datetime, time, timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests.common import TransactionCase


class TestComplianceDailyA4(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env.company

        # Generic thresholds to make assertions deterministic
        cls.company.x_generic_min_hours = 1.0
        cls.company.x_generic_warn_pct = 0.20
        cls.company.x_generic_issue_pct = 0.40
        cls.company.x_delta_tolerance_ok = 0.01
        cls.company.x_delta_warn_hours = 0.5

        cls.department = cls.env["hr.department"].create(
            {
                "name": "Dept A4",
                # keep department thresholds empty so company ones apply
            }
        )

        cls.user = (
            cls.env["res.users"]
            .with_context(no_reset_password=True, mail_create_nosubscribe=True)
            .create(
                {
                    "name": "User A4",
                    "login": "user_a4@example.com",
                    "email": "user_a4@example.com",
                    "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
                }
            )
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Employee A4",
                "user_id": cls.user.id,
                "department_id": cls.department.id,
                "company_id": cls.company.id,
            }
        )

        # ---- Timesheet setup (project + analytic account + plan if required) ----
        cls.analytic_plan = cls.env["account.analytic.plan"].create({"name": "Plan A4"})

        analytic_vals = {
            "name": "Analytic A4",
            "company_id": cls.company.id,
        }
        if "plan_id" in cls.env["account.analytic.account"]._fields:
            analytic_vals["plan_id"] = cls.analytic_plan.id
        cls.analytic_account = cls.env["account.analytic.account"].create(analytic_vals)

        cls.project_normal = cls.env["project.project"].create(
            {
                "name": "Project Normal A4",
                "allow_timesheets": True,
                "analytic_account_id": cls.analytic_account.id,
                "company_id": cls.company.id,
            }
        )
        cls.project_generic = cls.env["project.project"].create(
            {
                "name": "Project Generic A4",
                "allow_timesheets": True,
                "analytic_account_id": cls.analytic_account.id,
                "company_id": cls.company.id,
            }
        )
        cls.company.x_generic_project_ids = [(6, 0, [cls.project_generic.id])]

        cls.Compliance = cls.env["timesheet.compliance"]
        cls.AAL = cls.env["account.analytic.line"]
        cls.Att = cls.env["hr.attendance"]

    def _make_attendance(self, day, hours):
        start_dt = datetime.combine(day, time(8, 0, 0))
        end_dt = start_dt + timedelta(hours=hours)
        self.Att.create(
            {
                "employee_id": self.employee.id,
                "check_in": start_dt,
                "check_out": end_dt,
            }
        )

    def _make_timesheet(self, day, hours, project):
        vals = {
            "name": "TS",
            "date": day,
            "unit_amount": hours,
            "project_id": project.id,
            "account_id": project.analytic_account_id.id,
            "company_id": self.company.id,
        }
        if "employee_id" in self.AAL._fields:
            vals["employee_id"] = self.employee.id
        else:
            vals["user_id"] = self.user.id
        self.AAL.create(vals)

    def test_a4_cron_creates_records_for_yesterday_and_day_before(self):
        fixed_today = fields.Date.from_string("2026-01-13")
        yesterday = fixed_today - timedelta(days=1)
        day_before = fixed_today - timedelta(days=2)

        with patch("odoo.fields.Date.context_today", return_value=fixed_today):
            self.Compliance._cron_compute_compliance()

        recs = self.Compliance.search(
            [
                ("employee_id", "=", self.employee.id),
                ("date", "in", [yesterday, day_before]),
            ]
        )
        self.assertEqual(
            len(recs),
            2,
            "Cron must create 1 record per employee for D-1 and D-2",
        )

    def test_a4_cron_computes_numbers_and_generic_metrics(self):
        fixed_today = fields.Date.from_string("2026-01-13")
        yesterday = fixed_today - timedelta(days=1)

        # Attendance 8h
        self._make_attendance(yesterday, 8)

        # Timesheet 8h total: 2h generic + 6h normal
        self._make_timesheet(yesterday, 2, self.project_generic)
        self._make_timesheet(yesterday, 6, self.project_normal)

        with patch("odoo.fields.Date.context_today", return_value=fixed_today):
            self.Compliance._cron_compute_compliance()

        rec = self.Compliance.search(
            [("employee_id", "=", self.employee.id), ("date", "=", yesterday)],
            limit=1,
        )
        self.assertTrue(rec, "Compliance record must exist")
        self.assertAlmostEqual(rec.attendance_hours, 8.0, places=2)
        self.assertAlmostEqual(rec.timesheet_hours, 8.0, places=2)
        self.assertAlmostEqual(rec.delta_hours, 0.0, places=2)

        self.assertAlmostEqual(rec.generic_hours, 2.0, places=2)
        self.assertAlmostEqual(rec.generic_pct, 0.25, places=4)
        self.assertEqual(
            rec.generic_state,
            "warn",
            "0.25 must be warn with company warn threshold 0.20",
        )

    def test_a4_does_not_override_justified(self):
        fixed_today = fields.Date.from_string("2026-01-13")
        yesterday = fixed_today - timedelta(days=1)

        rec = self.Compliance.create(
            {
                "employee_id": self.employee.id,
                "date": yesterday,
                "state": "justified",
            }
        )

        # Make delta 0 (would normally promote)
        self._make_attendance(yesterday, 8)
        self._make_timesheet(yesterday, 8, self.project_normal)

        with patch("odoo.fields.Date.context_today", return_value=fixed_today):
            self.Compliance._cron_compute_compliance()

        rec.invalidate_recordset()
        self.assertEqual(rec.state, "justified", "Justified must never be overwritten")
        self.assertAlmostEqual(rec.delta_hours, 0.0, places=2)

    def test_a4_recomputes_fixed_to_current_state(self):
        fixed_today = fields.Date.from_string("2026-01-13")
        yesterday = fixed_today - timedelta(days=1)

        rec = self.Compliance.create(
            {
                "employee_id": self.employee.id,
                "date": yesterday,
                "state": "fixed",
            }
        )

        # Force mismatch: attendance 8, timesheet 6 => delta 2
        self._make_attendance(yesterday, 8)
        self._make_timesheet(yesterday, 6, self.project_normal)

        with patch("odoo.fields.Date.context_today", return_value=fixed_today):
            self.Compliance._cron_compute_compliance()

        rec.invalidate_recordset()
        self.assertEqual(
            rec.state,
            "issue",
            "Fixed must be recalculated to current compliance state",
        )
        self.assertAlmostEqual(rec.delta_hours, 2.0, places=2)

    def test_a4_excluded_employee_not_in_cron(self):
        """Cron must not create or update compliance for excluded employees."""
        fixed_today = fields.Date.from_string("2026-01-13")
        yesterday = fixed_today - timedelta(days=1)

        self.employee.x_timesheet_compliance_excluded = True
        self._make_attendance(yesterday, 8)
        self._make_timesheet(yesterday, 8, self.project_normal)

        with patch("odoo.fields.Date.context_today", return_value=fixed_today):
            self.Compliance._cron_compute_compliance()

        rec = self.Compliance.search(
            [("employee_id", "=", self.employee.id), ("date", "=", yesterday)],
            limit=1,
        )
        self.assertFalse(
            rec,
            "No compliance record must exist for excluded employee",
        )

    def test_a4_escalated_remains_escalated_while_unresolved(self):
        fixed_today = fields.Date.from_string("2026-01-14")
        yesterday = fixed_today - timedelta(days=1)

        rec = self.Compliance.create(
            {
                "employee_id": self.employee.id,
                "date": yesterday,
                "state": "escalated",
                "escalated_at": fields.Datetime.now(),
            }
        )

        # Force mismatch: attendance 8, timesheet 6 => delta 2 (issue-like)
        self._make_attendance(yesterday, 8)
        self._make_timesheet(yesterday, 6, self.project_normal)

        with patch("odoo.fields.Date.context_today", return_value=fixed_today):
            self.Compliance._cron_compute_compliance()

        rec.invalidate_recordset()
        self.assertEqual(rec.state, "escalated")
        self.assertAlmostEqual(rec.delta_hours, 2.0, places=2)

    def test_a4_escalated_returns_to_ok_when_resolved(self):
        fixed_today = fields.Date.from_string("2026-01-15")
        yesterday = fixed_today - timedelta(days=1)

        rec = self.Compliance.create(
            {
                "employee_id": self.employee.id,
                "date": yesterday,
                "state": "escalated",
                "escalated_at": fields.Datetime.now(),
            }
        )

        # Balanced day: attendance 8, timesheet 8 => ok
        self._make_attendance(yesterday, 8)
        self._make_timesheet(yesterday, 8, self.project_normal)

        with patch("odoo.fields.Date.context_today", return_value=fixed_today):
            self.Compliance._cron_compute_compliance()

        rec.invalidate_recordset()
        self.assertEqual(rec.state, "ok")
        self.assertTrue(rec.resolved_at)
        self.assertEqual(rec.resolved_from_state, "escalated")
