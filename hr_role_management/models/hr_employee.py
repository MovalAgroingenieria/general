from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    role_assignment_ids = fields.One2many(
        'hr.role.assignment',
        'employee_id',
        string='Role Assignments',
    )
