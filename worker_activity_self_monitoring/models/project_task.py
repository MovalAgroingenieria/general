# models/project_task.py
from odoo import fields, models


class ProjectTask(models.Model):
    _inherit = "project.task"

    task_running = fields.Boolean(string="Tarea en ejecución", default=False)
    starter_user_id = fields.Many2one("res.users", string="Usuario que inició la tarea")
    start_time = fields.Datetime(string="Hora de inicio")
