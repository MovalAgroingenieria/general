# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _
from datetime import date, timedelta


class BulkPreferencesWizard(models.TransientModel):
    _name = 'hr.telework.bulk.preferences.wizard'
    _description = 'Bulk Telework Preferences Configuration'

    employee_ids = fields.Many2many(
        comodel_name='hr.employee',
        relation='bulk_preferences_wizard_employee_rel',
        column1='wizard_id',
        column2='employee_id',
        string='Employees',
        default=lambda self: self._default_employees(),
    )

    auto_generate_week = fields.Boolean(
        string='Enable Auto Generation',
        default=True
    )

    monday_preference = fields.Selection([
            ('remote', _('Remote Work')),
            ('onsite', _('On-site')),
            ('flexible', _('Flexible')),
        ],
        string='Monday',
        default='onsite',
    )

    tuesday_preference = fields.Selection([
            ('remote', _('Remote Work')),
            ('onsite', _('On-site')),
            ('flexible', _('Flexible')),
        ],
        string='Tuesday',
        default='onsite',
    )

    wednesday_preference = fields.Selection([
            ('remote', _('Remote Work')),
            ('onsite', _('On-site')),
            ('flexible', _('Flexible')),
        ],
        string='Wednesday',
        default='onsite',
    )

    thursday_preference = fields.Selection([
            ('remote', _('Remote Work')),
            ('onsite', _('On-site')),
            ('flexible', _('Flexible')),
        ],
        string='Thursday',
        default='onsite',
    )

    friday_preference = fields.Selection([
            ('remote', _('Remote Work')),
            ('onsite', _('On-site')),
            ('flexible', _('Flexible')),
        ],
        string='Friday',
        default='onsite',
    )

    generate_current_week = fields.Boolean(
        string='Generate current week too',
        default=False,
        help='Generate schedule for current week in addition to next week',
    )

    @api.model
    def _default_employees(self):
        context = self.env.context
        if (context.get('active_model') == 'hr.employee' and
                context.get('active_ids')):
            return context.get('active_ids')
        return False

    def _refresh_views_and_cache(self, records=None):
        """Utility method to refresh views and cache"""
        self.env['hr.telework.day'].invalidate_cache()
        self.env['hr.employee'].invalidate_cache()
        self.env['office.workstation'].invalidate_cache()

        if records:
            try:
                if hasattr(records, '_compute_total_availability'):
                    records._compute_total_availability()
            except Exception:
                pass

    def action_apply_preferences(self):
        """Apply configured preferences to selected employees"""
        if not self.employee_ids:
            return {'type': 'ir.actions.act_window_close'}

        values = {
            'auto_generate_week': self.auto_generate_week,
            'monday_preference': self.monday_preference,
            'tuesday_preference': self.tuesday_preference,
            'wednesday_preference': self.wednesday_preference,
            'thursday_preference': self.thursday_preference,
            'friday_preference': self.friday_preference,
        }

        self.employee_ids.write(values)

        if self.generate_current_week:
            today = date.today()
            monday_current = today - timedelta(days=today.weekday())

            for employee in self.employee_ids:
                if employee.department_id:
                    employee.generate_week_schedule(monday_current)

        created_records = self.env['hr.telework.day']
        for employee in self.employee_ids:
            if employee.department_id:
                created = employee.generate_week_schedule()
                created_records |= created

        # Invalidate cache and show result
        self._refresh_views_and_cache(created_records)
        # Invalidate cache to update original view
        # self._refresh_views_and_cache(created_records)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_only_save_preferences(self):
        """Only save preferences without generating schedules"""
        if not self.employee_ids:
            return {'type': 'ir.actions.act_window_close'}

        values = {
            'auto_generate_week': self.auto_generate_week,
            'monday_preference': self.monday_preference,
            'tuesday_preference': self.tuesday_preference,
            'wednesday_preference': self.wednesday_preference,
            'thursday_preference': self.thursday_preference,
            'friday_preference': self.friday_preference,
        }

        self.employee_ids.write(values)

        self._refresh_views_and_cache()

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
