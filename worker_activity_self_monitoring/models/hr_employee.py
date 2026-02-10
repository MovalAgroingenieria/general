# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def get_current_attendance_time(self):
        """Return worked time since check-in for the current user employee.

        Uses UTC for the delta so the result is consistent in tests and
        regardless of user timezone.
        """
        # Use self when already the current user's employee (keeps in-memory
        # state e.g. in tests); otherwise resolve by user_id
        if self and len(self) == 1 and self.user_id == self.env.user:
            employee = self
        else:
            employee = self.env["hr.employee"].search(
                [("user_id", "=", self.env.user.id)],
                limit=1,
            )
        if not employee:
            return {"hours": 0, "minutes": 0, "display": "0h 0m"}

        if not employee.last_attendance_id or employee.attendance_state != "checked_in":
            return {"hours": 0, "minutes": 0, "display": "0h 0m"}

        check_in = employee.last_attendance_id.check_in
        if not check_in:
            return {"hours": 0, "minutes": 0, "display": "0h 0m"}

        now_utc = fields.Datetime.now()
        total_seconds = max(int((now_utc - check_in).total_seconds()), 0)

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        return {
            "hours": hours,
            "minutes": minutes,
            "display": "%sh %sm" % (hours, minutes),
        }
