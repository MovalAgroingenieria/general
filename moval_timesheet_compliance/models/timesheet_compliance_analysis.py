# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import api, fields, models


class TimesheetComplianceAnalysis(models.Model):
    _inherit = "timesheet.compliance"

    @api.model
    def action_open_analysis_today(self):
        today = fields.Date.context_today(self)
        return self._get_analysis_action_with_domain([("date", "=", today)])

    @api.model
    def action_open_analysis_yesterday(self):
        today = fields.Date.context_today(self)
        yesterday = today - timedelta(days=1)
        return self._get_analysis_action_with_domain([("date", "=", yesterday)])

    @api.model
    def action_open_analysis_this_week(self):
        today = fields.Date.context_today(self)
        start_week = today - timedelta(days=today.weekday())
        end_week = start_week + timedelta(days=6)
        domain = [("date", ">=", start_week), ("date", "<=", end_week)]
        return self._get_analysis_action_with_domain(domain)

    @api.model
    def action_open_analysis_this_month(self):
        today = fields.Date.context_today(self)
        start_month = today.replace(day=1)
        return self._get_analysis_action_with_domain(
            [("date", ">=", start_month), ("date", "<=", today)]
        )

    def _get_analysis_action_with_domain(self, domain):
        action = self.env.ref(
            "moval_timesheet_compliance.action_moval_timesheet_compliance_pivot",
            raise_if_not_found=False,
        )
        if not action:
            return {}
        result = action.read()[0]
        result["domain"] = domain
        return result
