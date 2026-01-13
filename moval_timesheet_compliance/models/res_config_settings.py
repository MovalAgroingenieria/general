# Copyright 2026 Moval
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # -------------------------------------------------------------------------
    # Generic allocation (E)
    # -------------------------------------------------------------------------

    x_generic_project_ids = fields.Many2many(
        related="company_id.x_generic_project_ids",
        readonly=False,
    )
    x_generic_warn_pct = fields.Float(
        related="company_id.x_generic_warn_pct",
        readonly=False,
    )
    x_generic_issue_pct = fields.Float(
        related="company_id.x_generic_issue_pct",
        readonly=False,
    )
    x_generic_min_hours = fields.Float(
        related="company_id.x_generic_min_hours",
        readonly=False,
    )

    # -------------------------------------------------------------------------
    # Timer watchdog (F)
    # -------------------------------------------------------------------------

    x_timer_max_active_hours = fields.Float(
        related="company_id.x_timer_max_active_hours",
        readonly=False,
    )
    x_timer_notify_cooldown_hours = fields.Float(
        related="company_id.x_timer_notify_cooldown_hours",
        readonly=False,
    )
    x_timer_check_no_attendance = fields.Boolean(
        related="company_id.x_timer_check_no_attendance",
        readonly=False,
    )
    x_timer_stop_on_checkout = fields.Boolean(
        related="company_id.x_timer_stop_on_checkout",
        readonly=False,
    )
    x_timer_escalation_enabled = fields.Boolean(
        related="company_id.x_timer_escalation_enabled",
        readonly=False,
    )
    x_timer_escalation_after_count = fields.Integer(
        related="company_id.x_timer_escalation_after_count",
        readonly=False,
    )
    x_timer_escalation_window_days = fields.Integer(
        related="company_id.x_timer_escalation_window_days",
        readonly=False,
    )
    x_timer_escalation_cooldown_hours = fields.Float(
        related="company_id.x_timer_escalation_cooldown_hours",
        readonly=False,
    )
