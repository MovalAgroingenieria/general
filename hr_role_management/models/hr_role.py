# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api


class HrRole(models.Model):
    _name = "hr.role"
    _description = "Role"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "department_id, level_id, name"

    name = fields.Char(
        required=True,
        tracking=True,
    )

    description = fields.Html(
        string="General Description",
    )

    department_id = fields.Many2one(
        "hr.department",
        required=True,
        ondelete="restrict",
        tracking=True,
    )

    level_id = fields.Many2one(
        "hr.level",
        string="Level",
        required=True,
        tracking=True,
        ondelete="restrict",
    )

    tasks_desc = fields.Html(
        string="Tasks and Responsibilities",
    )

    competencies_desc = fields.Html(
        string="Recommended Competencies",
    )

    assignment_ids = fields.One2many(
        "hr.role.assignment",
        "role_id",
        string="Assignments",
    )

    employee_count = fields.Integer(
        string="Number of Employees",
        compute="_compute_employee_count",
        store=False,
    )

    _sql_constraints = [
        (
            "name_department_uniq",
            "unique(name, department_id, level_id)",
            "A role with the same name, level, and department already exists.",
        ),
    ]

    @api.depends('assignment_ids.state')
    def _compute_employee_count(self):
        for role in self:
            count = sum(1 for a in role.assignment_ids if a.state != 'draft')
            role.employee_count = count
