# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProjectTask(models.Model):
    _inherit = "project.task"

    task_running = fields.Boolean(string="Task running", default=False)
    starter_user_id = fields.Many2one(
        comodel_name="res.users",
        string="User who started the task",
        ondelete="set null",
        index=True,
    )
    start_time = fields.Datetime(string="Start time", index=True)

    @api.constrains("task_running", "starter_user_id", "start_time")
    def _check_task_running_consistency(self):
        for task in self:
            if task.task_running and (not task.starter_user_id or not task.start_time):
                raise ValidationError(
                    task.env._(
                        "When a task is marked as running, both the starter "
                        "user and start time must be set."
                    )
                )
            if not task.task_running and (task.starter_user_id or task.start_time):
                raise ValidationError(
                    task.env._(
                        "When a task is not running, starter user and start "
                        "time must be empty."
                    )
                )

    @api.onchange("task_running")
    def _onchange_task_running(self):
        for task in self:
            if not task.task_running:
                task.starter_user_id = False
                task.start_time = False
