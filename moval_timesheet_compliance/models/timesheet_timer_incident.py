# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class TimesheetTimerIncident(models.Model):
    _name = "timesheet.timer.incident"
    _description = "Timesheet Timer Incident"
    _order = "create_date desc"

    timer_ref = fields.Reference(
        selection="_selection_timer_models",
        required=True,
        index=True,
    )
    employee_id = fields.Many2one("hr.employee", required=True, index=True)
    user_id = fields.Many2one("res.users", related="employee_id.user_id", store=True)
    department_id = fields.Many2one(
        "hr.department",
        related="employee_id.department_id",
        store=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    incident_type = fields.Selection(
        selection=[
            ("long_running", "Timer running too long"),
            ("no_attendance", "Timer running without attendance"),
            ("checkout_with_timer", "Checkout with active timer"),
        ],
        required=True,
        index=True,
    )

    timer_started_at = fields.Datetime(readonly=True)
    duration_hours = fields.Float(readonly=True)

    first_seen_at = fields.Datetime(readonly=True)
    last_seen_at = fields.Datetime(readonly=True)

    last_notified_at = fields.Datetime(readonly=True)
    notify_count = fields.Integer(readonly=True, default=0)

    escalated_at = fields.Datetime(readonly=True)
    escalated_count = fields.Integer(readonly=True, default=0)

    is_resolved = fields.Boolean(default=False, index=True)
    resolved_at = fields.Datetime(readonly=True)

    note = fields.Text()

    @api.model
    def _selection_timer_models(self):
        res = []
        if "project.task" in self.env:
            res.append(("project.task", "Task (project.task)"))

        icp = self.env["ir.config_parameter"].sudo()
        model_name = icp.get_param("moval_timesheet.timer_model_name")
        if (
            model_name
            and model_name in self.env
            and (model_name, model_name) not in res
        ):
            res.append((model_name, model_name))

        return res
