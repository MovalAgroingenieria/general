# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    x_generic_project_ids = fields.Many2many(
        comodel_name="project.project",
        string="Generic Projects",
        help="Projects considered generic for timesheet quality evaluation.",
    )

    x_compliance_excluded_project_ids = fields.Many2many(
        comodel_name="project.project",
        relation="res_company_compliance_excl_project_rel",
        column1="res_company_id",
        column2="project_id",
        string="Compliance-Excluded Projects",
        help=(
            "Timesheet lines on these projects are ignored when computing total "
            "compliance time (for attendance vs timesheet delta) and in project/task "
            "email breakdowns, so internal absence- or leave-like projects do not create "
            "false positives. Such projects are also removed from the generic (quality) "
            "denominator/numerator, even if they are listed as generic projects. "
            "Unconfigured projects (lines without a project) are not excluded by this list."
        ),
    )

    x_generic_warn_pct = fields.Float(
        string="Generic Warning Threshold (%)",
        help="Generic allocation percentage triggering a warning.",
    )
    x_generic_issue_pct = fields.Float(
        string="Generic Issue Threshold (%)",
        help="Generic allocation percentage triggering an issue.",
    )
    x_generic_min_hours = fields.Float(
        string="Minimum Hours for Generic Evaluation",
        default=3.0,
        help=(
            "Minimum total timesheet hours required " "to evaluate generic allocation."
        ),
    )

    # Delta (attendance vs timesheet) thresholds
    # -------------------------------------------------------------------------
    x_delta_tolerance_ok = fields.Float(
        string="Delta tolerance (OK)",
        default=0.01,
        help=(
            "Difference in hours between attendance and timesheet "
            "below which state is OK (e.g. 0.01)."
        ),
    )
    x_delta_warn_hours = fields.Float(
        string="Delta warning threshold (hours)",
        default=0.5,
        help=(
            "If the absolute difference is above tolerance but ≤ this value, "
            "state is Warning; above this, Issue."
        ),
    )

    # Timer watchdog (F phase)
    # -------------------------------------------------------------------------

    x_timer_max_active_hours = fields.Float(
        string="Timer Max Active Hours",
        default=6.0,
        help=(
            "Default maximum time (in hours) a timer may run before a long-running "
            "incident is created. Lower values are stricter. Departments may set their "
            "own limit; leave a department value empty to use this default."
        ),
    )
    x_timer_notify_cooldown_hours = fields.Float(
        string="Timer Notify Cooldown (Hours)",
        default=6.0,
        help=(
            "Default minimum time (in hours) between repeat employee notifications for the "
            "same open timer incident. Lower means more frequent reminders, higher means less "
            "frequent. Departments can override; leave a department value empty to use this."
        ),
    )
    x_timer_check_no_attendance = fields.Boolean(
        string="Detect timers without attendance",
        default=True,
        help=(
            "Create an incident if a timer is running while the employee "
            "has no active attendance."
        ),
    )
    x_timer_stop_on_checkout = fields.Boolean(
        string="Stop timer on checkout",
        default=False,
        help=(
            "If enabled, attempt to stop/pause the timer automatically "
            "on employee checkout."
        ),
    )

    x_timer_escalation_enabled = fields.Boolean(
        string="Enable Timer Escalation",
        default=False,
        help=(
            "Escalate recurring timer incidents to the department manager "
            "(with cooldown)."
        ),
    )
    x_timer_escalation_after_count = fields.Integer(
        string="Escalate After Notifications",
        default=3,
        help=(
            "Escalate after this many employee notifications for the same "
            "incident type within the window."
        ),
    )
    x_timer_escalation_window_days = fields.Integer(
        string="Escalation Window (Days)",
        default=7,
        help=(
            "Time window (in days) used to count notifications " "before escalating."
        ),
    )
    x_timer_escalation_cooldown_hours = fields.Float(
        string="Escalation Cooldown (Hours)",
        default=24.0,
        help="Minimum hours between escalations for the same open incident.",
    )
