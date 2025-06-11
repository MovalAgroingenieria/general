from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    employee_role_assignment_ids = fields.One2many(
        related='employee_id.role_assignment_ids',
        string='Role Assignments',
        readonly=True,
    )
