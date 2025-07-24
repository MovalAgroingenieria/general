# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields


class HrEmployeeFeedbackNoteType(models.Model):
    _name = 'hr.employee.feedback.note.type'
    _description = 'Type of Feedback Note'
    _order = 'name'

    name = fields.Char(
            string='Name',
            required=True,
    )
