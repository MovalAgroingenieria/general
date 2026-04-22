# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# pylint: disable=invalid-name,protected-access

from datetime import date as py_date

from odoo.tests.common import TransactionCase

from .common import cleanup_employee_workday_for_tests, skip_compliance_recompute_on


class TestComplianceDailyA1(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        cls.user = (
            cls.env["res.users"]
            .with_context(no_reset_password=True, mail_create_nosubscribe=True)
            .create(
                {
                    "name": "Compliance User",
                    "login": "compliance.user@test.invalid",
                    "email": "compliance.user@test.invalid",
                    "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
                }
            )
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "John Compliance",
                "user_id": cls.user.id,
            }
        )

        analytic_account_model = cls.env["account.analytic.account"]
        plan_id = False
        if "plan_id" in analytic_account_model._fields:
            plan_field = analytic_account_model._fields["plan_id"]
            plan_model = cls.env[plan_field.comodel_name]
            plan_vals = {"name": "Test Plan"}
            if "company_id" in plan_model._fields:
                plan_vals["company_id"] = cls.company.id
            plan_id = plan_model.create(plan_vals).id

        analytic_vals = {
            "name": "Timesheet Analytic Account",
            "company_id": cls.company.id,
        }
        if "plan_id" in analytic_account_model._fields:
            analytic_vals["plan_id"] = plan_id

        cls.analytic_account = analytic_account_model.create(analytic_vals)

        cls.project_generic = cls.env["project.project"].create(
            {
                "name": "Generic Project",
                "analytic_account_id": cls.analytic_account.id,
            }
        )

        cls.company.x_generic_project_ids = [(6, 0, [cls.project_generic.id])]
        cls.company.x_generic_min_hours = 3.0
        cls.company.x_generic_warn_pct = 0.5
        cls.company.x_generic_issue_pct = 0.8
        cls.company.x_delta_tolerance_ok = 0.01
        cls.company.x_delta_warn_hours = 0.5

        cls.compliance_model = cls.env["timesheet.compliance"]

    def _create_timesheet_line(self, day, hours, name="Work", project=False, **kw):
        e = kw.pop("env", None) or self.env
        if kw:
            raise TypeError("unexpected keyword arguments: %r" % (kw,))
        vals = {
            "name": name,
            "date": day,
            "unit_amount": hours,
            "employee_id": self.employee.id,
            "account_id": self.analytic_account.id,
        }
        if project:
            vals["project_id"] = project.id
        return e["account.analytic.line"].create(vals)

    def test_compute_ok_when_delta_zero(self):
        day = py_date(2099, 1, 10)
        cleanup_employee_workday_for_tests(self.env, self.employee, day)

        with skip_compliance_recompute_on(self.env) as e:
            e["hr.attendance"].create(
                {
                    "employee_id": self.employee.id,
                    "check_in": "2099-01-10 09:00:00",
                    "check_out": "2099-01-10 17:00:00",
                }
            )
            self._create_timesheet_line(
                day,
                8.0,
                name="Work",
                project=self.project_generic,
                env=e,
            )

        # Single day/company: avoid multi-company compute side effects in shared DBs.
        self.compliance_model.with_company(self.company).sudo()._compute_employee_date(
            self.employee, day
        )
        rec = self.compliance_model.search(
            [("employee_id", "=", self.employee.id), ("date", "=", day)],
            limit=1,
        )
        self.assertTrue(rec)
        self.assertEqual(rec.attendance_hours, 8.0)
        self.assertEqual(rec.timesheet_hours, 8.0)
        self.assertEqual(rec.delta_hours, 0.0)
        self.assertEqual(rec.state, "ok")

    def test_generic_state_thresholds(self):
        day = py_date(2026, 1, 11)

        self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": "2026-01-11 09:00:00",
                "check_out": "2026-01-11 17:00:00",
            }
        )
        self._create_timesheet_line(
            day,
            4.0,
            name="Generic",
            project=self.project_generic,
        )
        self._create_timesheet_line(
            day,
            1.0,
            name="Non generic",
            project=False,
        )

        self.compliance_model.compute_for_dates([day])
        rec = self.compliance_model.search(
            [("employee_id", "=", self.employee.id), ("date", "=", day)],
            limit=1,
        )
        self.assertEqual(rec.timesheet_hours, 5.0)
        self.assertEqual(rec.generic_hours, 4.0)
        self.assertAlmostEqual(rec.generic_pct, 0.8, places=6)
        self.assertEqual(rec.generic_state, "issue")

    def test_compute_skips_excluded_employees(self):
        self.employee.x_timesheet_compliance_excluded = True
        day = py_date(2026, 1, 15)

        self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": "2026-01-15 09:00:00",
                "check_out": "2026-01-15 17:00:00",
            }
        )
        self._create_timesheet_line(day, 8.0, name="Work", project=self.project_generic)

        self.compliance_model.compute_for_dates([day])
        rec = self.compliance_model.search(
            [("employee_id", "=", self.employee.id), ("date", "=", day)],
            limit=1,
        )
        self.assertFalse(
            rec,
            "No compliance record must be created for excluded employee",
        )

    def test_delta_state_warn_when_within_warn_threshold(self):
        """State is warn when |delta| > tolerance_ok but <= warn_hours."""
        self.company.x_delta_tolerance_ok = 0.01
        self.company.x_delta_warn_hours = 0.5
        day = py_date(2026, 1, 16)

        self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": "2026-01-16 09:00:00",
                "check_out": "2026-01-16 17:00:00",
            }
        )
        self._create_timesheet_line(day, 7.5, name="Work", project=self.project_generic)

        self.compliance_model.compute_for_dates([day])
        rec = self.compliance_model.search(
            [("employee_id", "=", self.employee.id), ("date", "=", day)],
            limit=1,
        )
        self.assertTrue(rec)
        self.assertAlmostEqual(rec.delta_hours, 0.5, places=2)
        self.assertEqual(rec.state, "warn")

    def test_delta_state_issue_when_above_warn_threshold(self):
        """State is issue when |delta| > warn_hours."""
        self.company.x_delta_tolerance_ok = 0.01
        self.company.x_delta_warn_hours = 0.5
        day = py_date(2026, 1, 17)

        self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": "2026-01-17 09:00:00",
                "check_out": "2026-01-17 17:00:00",
            }
        )
        self._create_timesheet_line(day, 6.0, name="Work", project=self.project_generic)

        self.compliance_model.compute_for_dates([day])
        rec = self.compliance_model.search(
            [("employee_id", "=", self.employee.id), ("date", "=", day)],
            limit=1,
        )
        self.assertTrue(rec)
        self.assertAlmostEqual(rec.delta_hours, 2.0, places=2)
        self.assertEqual(rec.state, "issue")

    def test_delta_promotion_to_fixed_when_corrected(self):
        """When delta <= tolerance after warn/issue, state becomes fixed."""
        self.company.x_delta_tolerance_ok = 0.01
        self.company.x_delta_warn_hours = 0.5
        day = py_date(2026, 1, 18)

        self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": "2026-01-18 09:00:00",
                "check_out": "2026-01-18 17:00:00",
            }
        )
        self._create_timesheet_line(day, 6.0, name="Work", project=self.project_generic)

        self.compliance_model.compute_for_dates([day])
        rec = self.compliance_model.search(
            [("employee_id", "=", self.employee.id), ("date", "=", day)],
            limit=1,
        )
        self.assertEqual(rec.state, "issue")
        self.assertAlmostEqual(rec.delta_hours, 2.0, places=2)

        self._create_timesheet_line(
            day, 2.0, name="Extra", project=self.project_generic
        )
        self.compliance_model.compute_for_dates([day])
        rec.invalidate_recordset()
        rec = self.compliance_model.search(
            [("employee_id", "=", self.employee.id), ("date", "=", day)],
            limit=1,
        )
        self.assertAlmostEqual(rec.delta_hours, 0.0, places=2)
        self.assertEqual(
            rec.state,
            "fixed",
            "Delta corrected within tolerance must promote to fixed",
        )
