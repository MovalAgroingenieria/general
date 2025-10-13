# Copyright 2025 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from datetime import date, timedelta


class BulkPreferencesWizard(models.TransientModel):
    _name = 'hr.telework.bulk.preferences.wizard'
    _description = 'Bulk Telework Preferences Configuration'

    employee_ids = fields.Many2many(
        'hr.employee', string='Employees',
        default=lambda self: self._default_employees())

    # General configuration
    auto_generate_week = fields.Boolean(
        string='Enable Auto Generation', default=True)

    # Daily preferences
    monday_preference = fields.Selection([
        ('remote', _('Remote Work')),
        ('onsite', _('On-site')),
        ('flexible', _('Flexible')),
    ], string='Monday', default='onsite')

    tuesday_preference = fields.Selection([
        ('remote', _('Remote Work')),
        ('onsite', _('On-site')),
        ('flexible', _('Flexible')),
    ], string='Tuesday', default='onsite')

    wednesday_preference = fields.Selection([
        ('remote', _('Remote Work')),
        ('onsite', _('On-site')),
        ('flexible', _('Flexible')),
    ], string='Wednesday', default='onsite')

    thursday_preference = fields.Selection([
        ('remote', _('Remote Work')),
        ('onsite', _('On-site')),
        ('flexible', _('Flexible')),
    ], string='Thursday', default='onsite')

    friday_preference = fields.Selection([
        ('remote', _('Remote Work')),
        ('onsite', _('On-site')),
        ('flexible', _('Flexible')),
    ], string='Friday', default='onsite')

    generate_current_week = fields.Boolean(
        string='Generate current week too', default=False,
        help='Generate schedule for current week in addition to next week')

    @api.model
    def _default_employees(self):
        context = self.env.context
        if (context.get('active_model') == 'hr.employee' and
                context.get('active_ids')):
            return context.get('active_ids')
        return False

    def _refresh_views_and_cache(self, records=None):
        """Utility method to refresh views and cache"""
        # Invalidate cache for related models
        self.env['hr.telework.day'].invalidate_cache()
        self.env['hr.employee'].invalidate_cache()
        self.env['office.workstation'].invalidate_cache()

        # If there are records, force recomputation of computed fields
        if records:
            try:
                # Try to recalculate availability if the method exists
                if hasattr(records, '_compute_total_availability'):
                    records._compute_total_availability()
            except Exception:
                # If recomputation fails, continue without error
                pass

    def action_apply_preferences(self):
        """Apply configured preferences to selected employees"""
        if not self.employee_ids:
            return {'type': 'ir.actions.act_window_close'}

        # Update employee preferences
        values = {
            'auto_generate_week': self.auto_generate_week,
            'monday_preference': self.monday_preference,
            'tuesday_preference': self.tuesday_preference,
            'wednesday_preference': self.wednesday_preference,
            'thursday_preference': self.thursday_preference,
            'friday_preference': self.friday_preference,
        }

        self.employee_ids.write(values)

        # Generate schedules if requested
        if self.generate_current_week:
            today = date.today()
            # Find Monday of current week
            monday_current = today - timedelta(days=today.weekday())

            for employee in self.employee_ids:
                if employee.department_id:
                    employee.generate_week_schedule(monday_current)

        # Generate next week
        created_records = self.env['hr.telework.day']
        for employee in self.employee_ids:
            if employee.department_id:
                created = employee.generate_week_schedule()
                created_records |= created

        # Invalidate cache and show result
        self._refresh_views_and_cache(created_records)

        # Invalidate cache to update original view
        self._refresh_views_and_cache(created_records)

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

        # Invalidate cache to update views
        self._refresh_views_and_cache()

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }


class WeeklyGenerationWizard(models.TransientModel):
    _name = 'hr.telework.weekly.generation.wizard'
    _description = 'Bulk Weekly Schedule Generation'

    employee_ids = fields.Many2many(
        'hr.employee', string='Employees',
        default=lambda self: self._default_employees())

    start_date = fields.Date(
        string='Start Date', required=True,
        default=lambda self: self._default_start_date())

    weeks_count = fields.Integer(
        string='Number of Weeks', default=1, required=True)

    override_existing = fields.Boolean(
        string='Override Existing', default=False,
        help='Override existing schedules')

    @api.model
    def _default_employees(self):
        context = self.env.context
        if (context.get('active_model') == 'hr.employee' and
                context.get('active_ids')):
            return context.get('active_ids')
        # By default, employees with auto generation enabled
        return self.env['hr.employee'].search([
            ('auto_generate_week', '=', True),
            ('active', '=', True),
            ('department_id', '!=', False)
        ])

    @api.model
    def _default_start_date(self):
        # By default, next Monday
        today = date.today()
        days_ahead = 7 - today.weekday()
        return today + timedelta(days=days_ahead)

    def _refresh_views_and_cache(self, records=None):
        """Utility method to refresh views and cache"""
        # Invalidate cache for related models
        self.env['hr.telework.day'].invalidate_cache()
        self.env['hr.employee'].invalidate_cache()
        self.env['office.workstation'].invalidate_cache()

        # If there are records, force recomputation of computed fields
        if records:
            try:
                # Try to recalculate availability if the method exists
                if hasattr(records, '_compute_total_availability'):
                    records._compute_total_availability()
            except Exception:
                # If recomputation fails, continue without error
                pass

    def action_generate_weeks(self):
        """Generate schedules for specified weeks"""
        if not self.employee_ids:
            return {'type': 'ir.actions.act_window_close'}

        created_records = self.env['hr.telework.day']

        for week in range(self.weeks_count):
            week_start = self.start_date + timedelta(weeks=week)

            # Ensure it's Monday
            if week_start.weekday() != 0:
                week_start = week_start - timedelta(days=week_start.weekday())

            for employee in self.employee_ids:
                if not employee.department_id:
                    continue

                # If not overriding, check existence
                if not self.override_existing:
                    existing_count = self.env['hr.telework.day'].search_count([
                        ('employee_id', '=', employee.id),
                        ('date', '>=', week_start),
                        ('date', '<', week_start + timedelta(days=7)),
                    ])
                    if existing_count >= 5:  # Already has complete schedule
                        continue

                # Generate or update the week
                if self.override_existing:
                    # Remove existing schedules for this week
                    existing = self.env['hr.telework.day'].search([
                        ('employee_id', '=', employee.id),
                        ('date', '>=', week_start),
                        ('date', '<', week_start + timedelta(days=7)),
                    ])
                    existing.unlink()

                created = employee.generate_week_schedule(week_start)
                created_records |= created

        # Invalidate cache to update all related views
        self._refresh_views_and_cache(created_records)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
