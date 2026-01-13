# Copyright 2026 Moval
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date as py_date

from odoo.tests.common import TransactionCase


class TestComplianceDailyA3(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = (
            cls.env["res.users"]
            .with_context(no_reset_password=True, mail_create_nosubscribe=True)
            .create(
                {
                    "name": "Compliance User A3",
                    "login": "compliance.user.a3@test.invalid",
                    "email": "compliance.user.a3@test.invalid",
                    "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
                }
            )
        )
        cls.department = cls.env["hr.department"].create({"name": "A3 Dept"})
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "John Telework",
                "user_id": cls.user.id,
                "department_id": cls.department.id,
            }
        )

        cls.compliance_model = cls.env["timesheet.compliance"]

    def test_a3_telework_true_without_timesheets(self):
        d = py_date(2026, 1, 12)

        # Telework day in remote mode (no timesheets created)
        self.env["hr.telework.day"].create(
            {
                "employee_id": self.employee.id,
                "department_id": self.department.id,
                "date": d,
                "mode": "remote",
                "state": "confirmed",
            }
        )

        self.compliance_model.compute_for_dates([d])

        rec = self.compliance_model.search(
            [("employee_id", "=", self.employee.id), ("date", "=", d)],
            limit=1,
        )
        self.assertTrue(rec, "Compliance record should be created")
        self.assertTrue(
            rec.telework, "Telework must be True when hr.telework.day is remote"
        )
        self.assertEqual(rec.timesheet_hours, 0.0)
        self.assertEqual(
            rec.state,
            "issue",
            "Telework with no timesheets must be issue by current rules",
        )

    def test_a3_telework_false_when_onsite(self):
        d = py_date(2026, 1, 13)

        self.env["hr.telework.day"].create(
            {
                "employee_id": self.employee.id,
                "department_id": self.department.id,
                "date": d,
                "mode": "onsite",
                "state": "confirmed",
            }
        )

        self.compliance_model.compute_for_dates([d])

        rec = self.compliance_model.search(
            [("employee_id", "=", self.employee.id), ("date", "=", d)],
            limit=1,
        )
        self.assertTrue(rec)
        self.assertFalse(rec.telework, "On-site must not be considered telework")
