# models/hr_employee.py
from odoo import models, api
from datetime import datetime
from pytz import timezone


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def get_current_attendance_time(self):
        """
        Calculate the hours worked today for the current user.
        Independent of timezone handling.
        """
        # Get current employee
        employee = self.search([("user_id", "=", self.env.user.id)], limit=1)
        if not employee:
            return {"hours": 0, "minutes": 0, "display": "0h 0m"}

        # Get last check-in
        if (not employee.last_attendance_id or
                employee.attendance_state != "checked_in"):
            return {"hours": 0, "minutes": 0, "display": "0h 0m"}

        # Get check-in time in server timezone
        check_in = employee.last_attendance_id.check_in
        if not check_in:
            return {"hours": 0, "minutes": 0, "display": "0h 0m"}

        # Get current time in server timezone
        now = datetime.now(timezone(self.env.user.tz or "UTC"))
        user_tz = timezone(self.env.user.tz or "UTC")
        check_in_tz = check_in.replace(tzinfo=user_tz)

        # Calculate difference
        diff = now - check_in_tz
        total_seconds = int(diff.total_seconds())

        # Ensure we don't have negative times
        if total_seconds < 0:
            total_seconds = 0

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        return {
            "hours": hours,
            "minutes": minutes,
            "display": f"{hours}h {minutes}m"
        }
