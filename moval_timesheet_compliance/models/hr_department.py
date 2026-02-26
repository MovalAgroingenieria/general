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

    # Timer watchdog: department overrides (optional)
    # -------------------------------------------------------------------------
    x_timer_max_active_hours = fields.Float(
        string="Timer max active hours (override)",
        help="If set, overrides the company limit for this department. "
        "Use a lower value for roles with many context switches (e.g. support, "
        "many tasks per day); leave empty to use company default.",
    )
    x_timer_notify_cooldown_hours = fields.Float(
        string="Timer notify cooldown hours (override)",
        help="If set, overrides the company notification cooldown for this department. "
        "Leave empty to use company default.",
    )
