# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# pylint: disable=invalid-name,protected-access

from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests.common import TransactionCase

from .dummy_timer import DummyTimer


class TestTimerWatchdogF1(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env.company
        cls.department = cls.env["hr.department"].create({"name": "Dept F1"})

        cls.user = cls.env["res.users"].create(
            {
                "name": "User F1",
                "login": "user_f1_test",
                "email": "user_f1@example.com",
            }
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Employee F1",
                "user_id": cls.user.id,
                "department_id": cls.department.id,
            }
        )

        cls.watchdog = cls.env["timesheet.timer.watchdog"]
        cls.Incident = cls.env["timesheet.timer.incident"].sudo()

    def test_f1_creates_incidents_and_respects_cooldown(self):
        self.company.write(
            {
                "x_timer_max_active_hours": 1.0,
                "x_timer_notify_cooldown_hours": 24.0,
                "x_timer_check_no_attendance": True,
                "x_timer_escalation_enabled": False,
            }
        )

        started_at = fields.Datetime.now() - timedelta(hours=2)
        timer = DummyTimer(timer_id=10, started_at=started_at, employee=self.employee)

        watchdog_cls = type(self.watchdog)

        with patch.object(
            watchdog_cls,
            "_get_active_timers",
            autospec=True,
            side_effect=lambda _self, employee=None: [timer],
        ), patch.object(
            watchdog_cls,
            "_has_active_attendance",
            autospec=True,
            return_value=False,
        ), patch.object(
            watchdog_cls,
            "_notify_employee",
            autospec=True,
            return_value=True,
        ) as mock_notify:
            # 1st run: creates 2 incidents (long_running + no_attendance) => 2 notifies
            self.watchdog.cron_watchdog_timers()
            self.assertEqual(mock_notify.call_count, 2)

            self.assertEqual(
                self.Incident.search_count(
                    [
                        ("timer_ref", "=", "project.task,10"),
                        ("incident_type", "=", "long_running"),
                        ("is_resolved", "=", False),
                    ]
                ),
                1,
            )
            self.assertEqual(
                self.Incident.search_count(
                    [
                        ("timer_ref", "=", "project.task,10"),
                        ("incident_type", "=", "no_attendance"),
                        ("is_resolved", "=", False),
                    ]
                ),
                1,
            )

            # 2nd run within cooldown: MUST NOT notify again and MUST NOT duplicate
            self.watchdog.cron_watchdog_timers()
            self.assertEqual(mock_notify.call_count, 2)

            # still open (should not be auto-resolved while timer is active)
            self.assertEqual(
                self.Incident.search_count(
                    [
                        ("timer_ref", "=", "project.task,10"),
                        ("incident_type", "=", "long_running"),
                        ("is_resolved", "=", False),
                    ]
                ),
                1,
            )
            self.assertEqual(
                self.Incident.search_count(
                    [
                        ("timer_ref", "=", "project.task,10"),
                        ("incident_type", "=", "no_attendance"),
                        ("is_resolved", "=", False),
                    ]
                ),
                1,
            )

            # notify_count must remain 1
            long_inc = self.Incident.search(
                [
                    ("timer_ref", "=", "project.task,10"),
                    ("incident_type", "=", "long_running"),
                    ("is_resolved", "=", False),
                ],
                limit=1,
            )
            noatt_inc = self.Incident.search(
                [
                    ("timer_ref", "=", "project.task,10"),
                    ("incident_type", "=", "no_attendance"),
                    ("is_resolved", "=", False),
                ],
                limit=1,
            )
            self.assertEqual(long_inc.notify_count, 1)
            self.assertEqual(noatt_inc.notify_count, 1)
            self.assertTrue(long_inc.last_notified_at)
            self.assertTrue(noatt_inc.last_notified_at)
