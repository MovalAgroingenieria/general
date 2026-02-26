# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# pylint: disable=invalid-name,protected-access

from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests.common import TransactionCase

from .dummy_timer import DummyTimer


class TestTimerWatchdogF2(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env.company
        cls.department = cls.env["hr.department"].create({"name": "Dept F2"})

        cls.user = cls.env["res.users"].create(
            {
                "name": "User F2",
                "login": "user_f2_test",
                "email": "user_f2@example.com",
            }
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Employee F2",
                "user_id": cls.user.id,
                "department_id": cls.department.id,
            }
        )

        cls.watchdog = cls.env["timesheet.timer.watchdog"]
        cls.incident_model = cls.env["timesheet.timer.incident"].sudo()

    def test_f2_checkout_creates_incident_and_forces_notification(self):
        self.company.write(
            {
                "x_timer_stop_on_checkout": False,
                "x_timer_notify_cooldown_hours": 24.0,
                "x_timer_escalation_enabled": False,
            }
        )

        started_at = fields.Datetime.now() - timedelta(minutes=30)
        timer = DummyTimer(timer_id=20, started_at=started_at, employee=self.employee)

        watchdog_cls = type(self.watchdog)

        with patch.object(
            watchdog_cls,
            "_get_active_timers",
            autospec=True,
            side_effect=lambda _self, employee=None: [timer],
        ), patch.object(
            watchdog_cls,
            "_notify_employee",
            autospec=True,
            return_value=True,
        ) as mock_notify:
            self.watchdog.handle_checkout(self.employee)

            self.assertEqual(mock_notify.call_count, 1)

        incident = self.incident_model.search(
            [
                ("timer_ref", "=", "project.task,20"),
                ("incident_type", "=", "checkout_with_timer"),
                ("is_resolved", "=", False),
            ],
            limit=1,
        )
        self.assertTrue(incident)
        self.assertGreaterEqual(incident.notify_count, 1)
        self.assertIn("Checkout detected", incident.note or "")
