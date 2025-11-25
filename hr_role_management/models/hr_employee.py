# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    role_assignment_ids = fields.One2many(
        'hr.role.assignment',
        'employee_id',
        string='Role Assignments',
    )

    def open_hr_roles(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Role Assignments',
            'res_model': 'hr.role.assignment',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
            'target': 'current',
        }
