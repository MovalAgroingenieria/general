# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrDepartment(models.Model):
    _inherit = "hr.department"

    x_generic_warn_pct = fields.Float(
        string="Generic Warning Threshold (%)",
        help="Department-specific generic allocation warning threshold.",
    )
    x_generic_issue_pct = fields.Float(
        string="Generic Issue Threshold (%)",
        help="Department-specific generic allocation issue threshold.",
    )

    # Timer watchdog: optional per-department values (see company for defaults)
    # -------------------------------------------------------------------------
    x_timer_max_active_hours = fields.Float(
        string="Max Active Timer (Hours)",
        help=(
            "Optional. Leave empty to use the company value (see Timesheet & Compliance in "
            "Settings). A positive value overrides the company for this department. "
            "Set lower than the company to detect long-running timers sooner (e.g. teams "
            "with many context switches, short-burst work). Set higher to be more lenient."
        ),
    )
    x_timer_notify_cooldown_hours = fields.Float(
        string="Notification Cooldown (Hours)",
        help=(
            "Optional. Leave empty to use the company value. A positive value overrides the "
            "company minimum time between repeat employee notifications for the same open "
            "incident. Set lower to re-notify more often; set higher to reduce noise. "
        ),
    )
