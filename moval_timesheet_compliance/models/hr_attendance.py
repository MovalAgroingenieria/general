# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# pylint: disable=translation-not-lazy

from odoo import api, models

# `worked_hours` and bucket membership can change on these.
ATT_RECOMPUTE_FIELDS = frozenset(
    {
        "check_in",
        "check_out",
        "employee_id",
    }
)


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    def _compliance_employee_id_date_tuples(self):
        """(employee_id, day) for compliance rows affected by these attendances."""
        compliance = self.env["timesheet.compliance"]
        pairs = set()
        for att in self:
            if not att.employee_id or not att.check_in:
                continue
            if (
                att.employee_id.x_timesheet_compliance_excluded
                or not att.employee_id.user_id
            ):
                continue
            the_day = compliance._compliance_date_for_attendance_checkin(
                att.check_in, att.employee_id
            )
            if the_day:
                pairs.add((att.employee_id.id, the_day))
        return pairs

    def _flush_compliance_recompute(self, pairs):
        if not pairs:
            return
        self.env["timesheet.compliance"].recompute_employee_date_pairs(pairs)

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        if not self.env.context.get("skip_timesheet_compliance_recompute"):
            recs._flush_compliance_recompute(recs._compliance_employee_id_date_tuples())
        return recs

    def write(self, vals):
        if not self:
            return super().write(vals)
        before = (
            self._compliance_employee_id_date_tuples()
            if not self.env.context.get("skip_timesheet_compliance_recompute")
            and (ATT_RECOMPUTE_FIELDS & set(vals))
            else set()
        )
        res = super().write(vals)

        # Watchdog: checkout with active timer
        if "check_out" in vals and vals.get("check_out"):
            watchdog = self.env["timesheet.timer.watchdog"]
            for att in self:
                if att.employee_id:
                    watchdog.handle_checkout(att.employee_id)

        if not self.env.context.get("skip_timesheet_compliance_recompute"):
            if not (ATT_RECOMPUTE_FIELDS & set(vals)):
                return res
            after = self._compliance_employee_id_date_tuples()
            self._flush_compliance_recompute(before | after)
        return res

    def unlink(self):
        if not self or self.env.context.get("skip_timesheet_compliance_recompute"):
            return super().unlink()
        env = self.env
        pairs = self._compliance_employee_id_date_tuples()
        res = super().unlink()
        env["timesheet.compliance"].recompute_employee_date_pairs(pairs)
        return res
