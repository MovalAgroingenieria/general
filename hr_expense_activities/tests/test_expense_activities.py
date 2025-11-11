# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# pylint: disable=invalid-name
from odoo import fields
from odoo.tests.common import TransactionCase, tagged

PARAM_KEY = "hr_expense_activities.with_activity"


@tagged("post_install", "-at_install")
class TestHrExpenseActivities(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ICPSudo = cls.env["ir.config_parameter"].sudo()
        cls.Product = cls.env["product.product"]
        cls.Employee = cls.env["hr.employee"]
        cls.Expense = cls.env["hr.expense"]
        cls.Sheet = cls.env["hr.expense.sheet"]

        # Basic expensable product
        cls.product = cls.Product.create(
            {
                "name": "Travel",
                "type": "service",
                "can_be_expensed": True,
            }
        )

        # Minimal employee
        cls.employee = cls.Employee.create({"name": "Test Employee"})

    @classmethod
    def _mk_sheet(cls, name="S1", amount=10.0):
        """Create a draft expense sheet with one expense line (v18 fields)."""
        exp = cls.Expense.create(
            {
                "name": "Taxi",
                "employee_id": cls.employee.id,
                "product_id": cls.product.id,
                # v18 uses total_amount (unit_amount was removed)
                "total_amount": amount,
                "payment_mode": "own_account",
                "date": fields.Date.context_today(cls.env.user),
            }
        )
        sheet = cls.Sheet.create(
            {
                "name": name,
                "employee_id": cls.employee.id,
                "payment_mode": "own_account",
                "expense_line_ids": [(6, 0, [exp.id])],
            }
        )
        return sheet

    def setUp(self):
        super().setUp()
        # Default: disable activities
        self.ICPSudo.set_param(PARAM_KEY, "False")

    def test_submit_without_activity_moves_draft_to_submit(self):
        sheet = self._mk_sheet(name="S-no-act")
        self.assertEqual(sheet.state, "draft")

        res = sheet.action_submit_sheet()
        sheet.invalidate_recordset()

        self.assertIn(res, (True, None))
        self.assertEqual(sheet.state, "submit")

    def test_multirecord_only_draft_is_updated(self):
        s1 = self._mk_sheet(name="S1-draft")
        s2 = self._mk_sheet(name="S2-draft")

        s2.write({"state": "submit"})
        self.assertEqual(s1.state, "draft")
        self.assertEqual(s2.state, "submit")

        res = (s1 | s2).action_submit_sheet()
        (s1 | s2).invalidate_recordset()

        self.assertIn(res, (True, None))
        self.assertEqual(s1.state, "submit")  # changed
        self.assertEqual(s2.state, "submit")  # unchanged

    def test_with_activity_delegates_to_native_flow(self):
        self.ICPSudo.set_param(PARAM_KEY, "True")
        sheet = self._mk_sheet(name="S-activity-on")
        self.assertEqual(sheet.state, "draft")

        res = sheet.action_submit_sheet()
        # Result depends on core flow; just ensure no exception and a sane return
        self.assertIn(res, (True, None))

    def test_idempotency_when_already_submitted(self):
        sheet = self._mk_sheet(name="S-idem")
        sheet.write({"state": "submit"})
        self.assertEqual(sheet.state, "submit")

        res = sheet.action_submit_sheet()
        sheet.invalidate_recordset()

        self.assertIn(res, (True, None))
        self.assertEqual(sheet.state, "submit")
