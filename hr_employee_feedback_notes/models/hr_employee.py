# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    feedback_note_ids = fields.One2many(
        comodel_name='hr.employee.feedback.note',
        inverse_name='employee_id',
        string='Feedback Notes',
    )
