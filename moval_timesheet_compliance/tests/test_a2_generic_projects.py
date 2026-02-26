# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date as py_date

from odoo.tests.common import TransactionCase


class TestComplianceDailyA2(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        cls.user = (
            cls.env["res.users"]
            .with_context(no_reset_password=True, mail_create_nosubscribe=True)
            .create(
                {
                    "name": "Compliance User A2",
                    "login": "compliance.user.a2@test.invalid",
                    "email": "compliance.user.a2@test.invalid",
                    "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
                }
            )
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "John Compliance A2",
                "user_id": cls.user.id,
            }
        )

        cls.department = cls.env["hr.department"].create({"name": "Dept A2"})
        cls.employee.department_id = cls.department.id

        # --- Analytic prerequisites (Odoo 16 may require plan_id on analytic account) ---
        analytic_vals = {
            "name": "Timesheet Analytic Account A2",
            "company_id": cls.company.id,
        }

        analytic_account_model = cls.env["account.analytic.account"]
        if "plan_id" in analytic_account_model._fields:
            plan_model = cls.env["account.analytic.plan"]

            # Reuse any existing plan first (avoids missing mandatory fields)
            plan_domain = []
            if "company_id" in plan_model._fields:
                plan_domain = [("company_id", "in", [cls.company.id, False])]
            plan = plan_model.search(plan_domain, limit=1)

            if not plan:
                plan_vals = {"name": "Test Plan A2"}
                if "company_id" in plan_model._fields:
                    plan_vals["company_id"] = cls.company.id
                plan = plan_model.create(plan_vals)

            analytic_vals["plan_id"] = plan.id

        cls.analytic_account = analytic_account_model.create(analytic_vals)

        cls.project_generic = cls.env["project.project"].create(
            {
                "name": "Generic Project A2",
                "analytic_account_id": cls.analytic_account.id,
            }
        )
        cls.project_non_generic = cls.env["project.project"].create(
            {
                "name": "Non Generic Project A2",
                "analytic_account_id": cls.analytic_account.id,
            }
        )

        cls.compliance_model = cls.env["timesheet.compliance"]

    def _create_timesheet_line(self, day, hours, name="Work", project=False):
        vals = {
            "name": name,
            "date": day,
            "unit_amount": hours,
            "employee_id": self.employee.id,
            "account_id": self.analytic_account.id,
        }
        if project:
            vals["project_id"] = project.id
        return self.env["account.analytic.line"].create(vals)

    def test_a2_changing_generic_projects_affects_computation(self):
        d = py_date(2026, 1, 12)

        self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": "2026-01-12 09:00:00",
                "check_out": "2026-01-12 17:00:00",
            }
        )

        # 4h in "generic candidate" + 1h non-generic
        self._create_timesheet_line(
            d, 4.0, name="A2 Generic", project=self.project_generic
        )
        self._create_timesheet_line(
            d, 1.0, name="A2 Non generic", project=self.project_non_generic
        )

        # First: generic project is configured -> generic_hours=4
        self.company.x_generic_project_ids = [(6, 0, [self.project_generic.id])]
        self.company.x_generic_min_hours = 0.0
        self.company.x_generic_warn_pct = 0.5
        self.company.x_generic_issue_pct = 0.8

        self.compliance_model.compute_for_dates([d])
        rec = self.compliance_model.search(
            [("employee_id", "=", self.employee.id), ("date", "=", d)],
            limit=1,
        )
        self.assertEqual(rec.timesheet_hours, 5.0)
        self.assertEqual(rec.generic_hours, 4.0)
        self.assertAlmostEqual(rec.generic_pct, 0.8, places=6)
        self.assertEqual(rec.generic_state, "issue")

        # Now: change generic list without deployment -> generic_hours becomes 0
        self.company.x_generic_project_ids = [(6, 0, [self.project_non_generic.id])]
        self.compliance_model.compute_for_dates([d])

        rec.invalidate_recordset()
        rec = self.compliance_model.search(
            [("employee_id", "=", self.employee.id), ("date", "=", d)],
            limit=1,
        )
        self.assertEqual(rec.timesheet_hours, 5.0)
        self.assertEqual(rec.generic_hours, 1.0)
        self.assertAlmostEqual(rec.generic_pct, 0.2, places=6)
        self.assertEqual(rec.generic_state, "ok")

    def test_a2_department_override_generic_thresholds(self):
        """Department-specific generic warn/issue pct override company thresholds."""
        d = py_date(2026, 1, 14)
        self.company.x_generic_project_ids = [(6, 0, [self.project_generic.id])]
        self.company.x_generic_min_hours = 0.0
        self.company.x_generic_warn_pct = 0.5
        self.company.x_generic_issue_pct = 0.8

        self.department.x_generic_warn_pct = 0.25
        self.department.x_generic_issue_pct = 0.50

        self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": "2026-01-14 09:00:00",
                "check_out": "2026-01-14 17:00:00",
            }
        )
        self._create_timesheet_line(
            d, 4.0, name="Generic", project=self.project_generic
        )
        self._create_timesheet_line(
            d, 6.0, name="Other", project=self.project_non_generic
        )

        self.compliance_model.compute_for_dates([d])
        rec = self.compliance_model.search(
            [("employee_id", "=", self.employee.id), ("date", "=", d)],
            limit=1,
        )
        self.assertEqual(rec.timesheet_hours, 10.0)
        self.assertEqual(rec.generic_hours, 4.0)
        self.assertAlmostEqual(rec.generic_pct, 0.4, places=6)
        self.assertEqual(
            rec.generic_state,
            "warn",
            "40% generic with dept warn=0.25 issue=0.50 must be warn",
        )
