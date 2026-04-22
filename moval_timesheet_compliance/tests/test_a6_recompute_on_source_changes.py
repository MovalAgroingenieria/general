# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# pylint: disable=invalid-name,protected-access

from datetime import datetime, time, timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestComplianceRecomputeOnSourceChanges(TransactionCase):
    """Hooks on AAL and hr.attendance must refresh timesheet.compliance in place."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.x_generic_min_hours = 20.0
        cls.company.x_generic_warn_pct = 0.20
        cls.company.x_generic_issue_pct = 0.40
        cls.company.x_delta_tolerance_ok = 0.01
        cls.company.x_delta_warn_hours = 0.5
        cls.company.x_compliance_excluded_project_ids = [(5, 0, 0)]

        cls.department = cls.env["hr.department"].create({"name": "Dept A6"})

        cls.user = (
            cls.env["res.users"]
            .with_context(no_reset_password=True, mail_create_nosubscribe=True)
            .create(
                {
                    "name": "User A6",
                    "login": "user_a6@example.com",
                    "email": "user_a6@example.com",
                    "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
                }
            )
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Employee A6",
                "user_id": cls.user.id,
                "department_id": cls.department.id,
                "company_id": cls.company.id,
            }
        )

        cls.analytic_plan = cls.env["account.analytic.plan"].create({"name": "Plan A6"})
        analytic_vals = {"name": "Analytic A6", "company_id": cls.company.id}
        if "plan_id" in cls.env["account.analytic.account"]._fields:
            analytic_vals["plan_id"] = cls.analytic_plan.id
        cls.analytic_account = cls.env["account.analytic.account"].create(analytic_vals)

        cls.project = cls.env["project.project"].create(
            {
                "name": "Project A6",
                "allow_timesheets": True,
                "analytic_account_id": cls.analytic_account.id,
                "company_id": cls.company.id,
            }
        )

        cls.Compliance = cls.env["timesheet.compliance"]
        cls.AAL = cls.env["account.analytic.line"]
        cls.Att = cls.env["hr.attendance"]

    def _day(self, offset=1):
        return fields.Date.from_string("2026-05-10") - timedelta(days=offset)

    def _make_line(self, day, hours, project, name="A6"):
        vals = {
            "name": name,
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
        return self.AAL.create(vals)

    def _make_attendance(self, day, work_hours, start_h=8):
        start_dt = datetime.combine(day, time(start_h, 0, 0))
        end_dt = start_dt + timedelta(hours=work_hours)
        return self.Att.create(
            {
                "employee_id": self.employee.id,
                "check_in": start_dt,
                "check_out": end_dt,
            }
        )

    def test_a6_editing_timesheet_line_updates_compliance(self):
        day = self._day(1)
        self._make_attendance(day, 7.0)
        line = self._make_line(day, 5.0, self.project)

        comp = self.Compliance.search(
            [("employee_id", "=", self.employee.id), ("date", "=", day)], limit=1
        )
        self.assertTrue(comp, "AAL create should trigger a compliance recompute")
        self.assertAlmostEqual(comp.timesheet_hours, 5.0, places=2)
        self.assertAlmostEqual(comp.attendance_hours, 7.0, places=2)

        line.write({"unit_amount": 7.0})
        comp.invalidate_recordset()
        self.assertAlmostEqual(comp.timesheet_hours, 7.0, places=2)
        self.assertAlmostEqual(comp.delta_hours, 0.0, places=2)

    def test_a6_editing_attendance_updates_compliance(self):
        day = self._day(2)
        self._make_line(day, 8.0, self.project)
        att2 = self._make_attendance(day, 4.0)

        comp = self.Compliance.search(
            [("employee_id", "=", self.employee.id), ("date", "=", day)], limit=1
        )
        self.assertTrue(comp)
        self.assertAlmostEqual(comp.attendance_hours, 4.0, places=2)
        self.assertLess(comp.delta_hours, -0.1)

        new_end = att2.check_in + timedelta(hours=8.0)
        att2.write({"check_out": new_end})
        comp.invalidate_recordset()
        self.assertAlmostEqual(comp.attendance_hours, 8.0, places=2)
        self.assertAlmostEqual(comp.delta_hours, 0.0, places=2)

    def test_a6_correcting_issue_can_move_to_fixed(self):
        day = self._day(3)
        self._make_attendance(day, 6.0)
        self._make_line(day, 2.0, self.project)
        comp = self.Compliance.search(
            [("employee_id", "=", self.employee.id), ("date", "=", day)], limit=1
        )
        self.assertTrue(comp)
        self.assertEqual(comp.state, "issue")

        line = self.AAL.search(
            [
                ("date", "=", day),
                ("project_id", "=", self.project.id),
            ],
            limit=1,
        )
        line.write({"unit_amount": 6.0})
        comp.invalidate_recordset()
        self.assertEqual(
            comp.state,
            "fixed",
            "Resolved mismatch for open incident states becomes fixed",
        )
        self.assertAlmostEqual(comp.delta_hours, 0.0, places=2)

    def test_a6_past_date_recomputation(self):
        past = self._day(7)
        self._make_line(past, 1.0, self.project, name="old")
        comp = self.Compliance.search(
            [("employee_id", "=", self.employee.id), ("date", "=", past)], limit=1
        )
        self.assertTrue(comp)
        before_ts = comp.timesheet_hours
        self.assertAlmostEqual(before_ts, 1.0, places=2)
        self._make_line(past, 0.5, self.project, name="extra")
        comp.invalidate_recordset()
        self.assertAlmostEqual(
            comp.timesheet_hours,
            1.5,
            places=2,
            msg="A second AAL for the same day must recompute",
        )
