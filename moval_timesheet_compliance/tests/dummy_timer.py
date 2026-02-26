# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


class DummyTimer:
    """Helper for timer watchdog tests: mimics a timer record (e.g. project.task)."""

    _name = "project.task"

    def __init__(self, timer_id, started_at, employee=None):
        self.id = timer_id
        self.timer_start = started_at
        self.employee_id = employee
        self.user_id = employee.user_id if employee else False

    def action_timer_stop(self):
        return True
