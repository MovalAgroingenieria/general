# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WeeklyTeleworkDeclaration(models.TransientModel):
    _name = 'weekly.telework.declaration'
    _description = 'Wizard for weekly telework declarations'

    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employee',
        required=True,
        default=lambda self: self.env.user.employee_id,
    )

    week_start_date = fields.Date(
        string='Week Monday',
        required=True,
        default=lambda self: self._get_monday()
    )

    monday_mode = fields.Selection([
            ('remote', 'Remote Work'),
            ('onsite', 'On-site'),
            ('no_work', 'No Work'),
        ],
        string='Monday',
        default='onsite',
    )

    tuesday_mode = fields.Selection([
            ('remote', 'Remote Work'),
            ('onsite', 'On-site'),
            ('no_work', 'No Work'),
        ],
        string='Tuesday',
        default='onsite',
    )

    wednesday_mode = fields.Selection([
            ('remote', 'Remote Work'),
            ('onsite', 'On-site'),
            ('no_work', 'No Work'),
        ],
        string='Wednesday',
        default='onsite',
    )

    thursday_mode = fields.Selection([
            ('remote', 'Remote Work'),
            ('onsite', 'On-site'),
            ('no_work', 'No Work'),
        ],
        string='Thursday',
        default='onsite',
    )

    friday_mode = fields.Selection([
            ('remote', 'Remote Work'),
            ('onsite', 'On-site'),
            ('no_work', 'No Work'),
        ],
        string='Friday',
        default='onsite',
    )

    @api.model
    def _get_monday(self):
        """Get Monday of current week"""
        today = fields.Date.today()
        monday = today - timedelta(days=today.weekday())
        return monday

    def _map_preference_to_mode(self, preference):
        """Convert preference to mode, flexible becomes on-site"""
        if preference == 'flexible':
            return 'onsite'
        return preference or 'onsite'

    @api.model
    def default_get(self, fields_list):
        """Load user preferences by default"""
        res = super().default_get(fields_list)

        employee = self.env.user.employee_id
        if employee:
            res['employee_id'] = employee.id

            preference_mapping = {
                'monday_mode': self._map_preference_to_mode(
                    employee.monday_preference),
                'tuesday_mode': self._map_preference_to_mode(
                    employee.tuesday_preference),
                'wednesday_mode': self._map_preference_to_mode(
                    employee.wednesday_preference),
                'thursday_mode': self._map_preference_to_mode(
                    employee.thursday_preference),
                'friday_mode': self._map_preference_to_mode(
                    employee.friday_preference),
            }

            for field_name, preference_value in preference_mapping.items():
                if field_name in fields_list:
                    res[field_name] = preference_value

        return res

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        """Update preferences when employee changes"""
        if self.employee_id:
            emp = self.employee_id
            self.monday_mode = self._map_preference_to_mode(
                emp.monday_preference)
            self.tuesday_mode = self._map_preference_to_mode(
                emp.tuesday_preference)
            self.wednesday_mode = self._map_preference_to_mode(
                emp.wednesday_preference)
            self.thursday_mode = self._map_preference_to_mode(
                emp.thursday_preference)
            self.friday_mode = self._map_preference_to_mode(
                emp.friday_preference)
        else:
            self.monday_mode = 'onsite'
            self.tuesday_mode = 'onsite'
            self.wednesday_mode = 'onsite'
            self.thursday_mode = 'onsite'
            self.friday_mode = 'onsite'

    def action_create_declarations(self):
        """Create declarations for the entire week"""
        self.ensure_one()

        if not self.employee_id:
            raise UserError(_('You must select an employee'))

        TeleworkDay = self.env['hr.telework.day']

        days_config = [
            (0, self.monday_mode),
            (1, self.tuesday_mode),
            (2, self.wednesday_mode),
            (3, self.thursday_mode),
            (4, self.friday_mode),
        ]

        created_declarations = []

        for day_offset, day_mode in days_config:
            current_date = self.week_start_date + timedelta(days=day_offset)

            existing = TeleworkDay.search([
                ('employee_id', '=', self.employee_id.id),
                ('date', '=', current_date),
            ])

            if day_mode == 'no_work':
                if existing and existing.state == 'draft':
                    existing.unlink()
                continue

            if existing:
                if existing.state == 'draft':
                    existing.mode = day_mode
                    created_declarations.append(existing)
            else:
                declaration = TeleworkDay.create({
                    'employee_id': self.employee_id.id,
                    'date': current_date,
                    'mode': day_mode,
                    'source': 'self',
                })
                created_declarations.append(declaration)

        if created_declarations:
            message = _(
                '%d declarations have been processed for week of %s') % (
                len(created_declarations),
                self.week_start_date.strftime('%d/%m/%Y')
            )

            overbooked_count = len([
                d for d in created_declarations if d.overbooked])
            if overbooked_count:
                message += _(
                    '\n⚠️ %d declarations with overbooking detected.'
                ) % overbooked_count

            self.env['hr.telework.day'].invalidate_cache()

            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
