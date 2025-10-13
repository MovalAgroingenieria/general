# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models, _
from odoo.exceptions import UserError


class Office(models.Model):
    _name = 'office.location'
    _description = 'Office'
    _order = 'name'

    name = fields.Char(string='Office Name', required=True)
    capacity = fields.Integer(
        string='Total Capacity', required=True, default=1,
        help='Total number of workstations that can be created in this office')

    image = fields.Binary(
        string='Office Image',
        help='Image of the floor plan or layout of the office')

    workstation_ids = fields.One2many(
        'office.workstation', 'office_id', string='Workstations')

    # Reviewers for pending assignment notifications
    reviewer_ids = fields.Many2many(
        'hr.employee',
        'office_reviewer_rel',
        'office_id',
        'employee_id',
        string='Telework Reviewers',
        help='Employees who will receive notifications about '
             'pending assignments in this office')

    active = fields.Boolean(default=True)

    def action_create_workstations(self):
        """Create workstations according to capacity"""
        self.ensure_one()

        current_count = len(self.workstation_ids)
        if current_count >= self.capacity:
            raise UserError(_(
                'This office already has all workstations created (%d/%d)'
            ) % (current_count, self.capacity))

        # Calculate how many workstations to create
        to_create = self.capacity - current_count

        if not to_create:
            raise UserError(_('No workstations pending creation'))

        # Get the next number
        existing_numbers = [
            int(ws.name.split('-')[-1]) for ws in self.workstation_ids
            if ws.name and '-' in ws.name and ws.name.split('-')[-1].isdigit()
        ]
        next_number = max(existing_numbers) + 1 if existing_numbers else 1

        # Create the workstations
        created_workstations = []
        for i in range(to_create):
            workstation = self.env['office.workstation'].create({
                'name': f'{self.name}-{next_number + i:03d}',
                'office_id': self.id,
            })
            created_workstations.append(workstation)

        # Invalidate cache so the view is updated
        self.invalidate_recordset(['workstation_ids'])

        return {
            'type': 'ir.actions.act_window',
            'name': _('Office: %s') % self.name,
            'res_model': 'office.location',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'notification_message': _(
                    '%d workstations have been created successfully.'
                ) % len(created_workstations),
                'notification_type': 'success',
            }
        }

    def action_view_workstations(self):
        """View the workstations of this office"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Workstations of %s') % self.name,
            'res_model': 'office.workstation',
            'view_mode': 'tree,form',
            'domain': [('office_id', '=', self.id)],
            'context': {'default_office_id': self.id},
            'target': 'current',
        }
