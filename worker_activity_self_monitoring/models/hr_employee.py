# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def get_current_attendance_time(self):
        """Return worked time today for the current user employee."""
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

        # pylint: disable=protected-access
        now = employee._get_today_now_user_tz()
        check_in_user_tz = employee._to_user_tz(check_in)

        total_seconds = max(int((now - check_in_user_tz).total_seconds()), 0)

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        return {
            "hours": hours,
            "minutes": minutes,
            "display": "%sh %sm" % (hours, minutes),
        }

    def _to_user_tz(self, dt_value):
        """Convert a naive/UTC datetime to user timezone-aware datetime."""
        self.ensure_one()
        return self.env.context_timestamp(self, dt_value)

    def _get_today_now_user_tz(self):
        """Return current datetime in user timezone (aware)."""
        self.ensure_one()
        return self.env.context_timestamp(self, self.env["ir.fields.datetime"].now())
