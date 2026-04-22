# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# pylint: disable=translation-not-lazy

from odoo import api, models

# Fields that can change how timesheet.compliance values are derived for a day.
AAL_RECOMPUTE_FIELDS = frozenset(
    {
        "date",
        "unit_amount",
        "project_id",
        "employee_id",
        "user_id",
        "company_id",
    }
)


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    def _compliance_employee_id_date_tuples(self):
        """(employee_id, line.date) for employees covered by the daily compliance run."""
        pairs = set()
        Employee = self.env["hr.employee"]
        for line in self:
            if not line.date:
                continue
            employee = False
            if "employee_id" in line._fields and line.employee_id:
                employee = line.employee_id
            elif line.user_id:
                employee = Employee.search([("user_id", "=", line.user_id.id)], limit=1)
            if (
                not employee
                or employee.x_timesheet_compliance_excluded
                or not employee.user_id
            ):
                continue
            pairs.add((employee.id, line.date))
        return pairs

    def _flush_compliance_recompute(self, pairs):
        if not pairs:
            return
        self.env["timesheet.compliance"].recompute_employee_date_pairs(pairs)

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        if not self.env.context.get("skip_timesheet_compliance_recompute"):
            lines._flush_compliance_recompute(
                lines._compliance_employee_id_date_tuples()
            )
        return lines

    def write(self, vals):
        if not self or self.env.context.get("skip_timesheet_compliance_recompute"):
            return super().write(vals)
        if not (AAL_RECOMPUTE_FIELDS & set(vals)):
            return super().write(vals)
        before = self._compliance_employee_id_date_tuples()
        res = super().write(vals)
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
