# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    def write(self, vals):
        res = super().write(vals)

        # Hook on checkout: when check_out is set (or updated)
        if "check_out" in vals and vals.get("check_out"):
            watchdog = self.env["timesheet.timer.watchdog"]
            for att in self:
                if att.employee_id:
                    watchdog.handle_checkout(att.employee_id)

        return res
