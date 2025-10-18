# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api


class HrEmployeeFeedbackNote(models.Model):
    _name = 'hr.employee.feedback.note'
    _description = 'Employee feedback note'
    _order = 'date desc'

    name = fields.Char(
        string='Title',
        required=True,
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
    )

    author_id = fields.Many2one(
        'res.users',
        string='Author',
        default=lambda self: self.env.uid,
        required=True,
    )

    date = fields.Date(
        string='Date',
        default=fields.Date.context_today,
        required=True,
    )

    note_text = fields.Html(
        string='Note Content',
    )

    active = fields.Boolean(
        default=True,
    )

    note_type_id = fields.Many2one(
        'hr.employee.feedback.note.type',
        string='Note Type',
        required=True,
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('registered', 'Registered'),
        ('archived', 'Archived')
    ],
        string='Status',
        default='draft',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('state') == 'draft' or not vals.get('state'):
                vals['state'] = 'registered'
        return super().create(vals_list)

    def write(self, vals):
        for rec in self:
            if rec.state == 'draft' and not vals.get('state'):
                vals['state'] = 'registered'
        return super().write(vals)

    def toggle_active(self):
        for rec in self:
            new_active = not rec.active
            new_state = 'registered' if new_active else 'archived'
            rec.write({
                'active': new_active,
                'state': new_state
            })
