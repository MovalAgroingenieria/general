# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _
from datetime import date, timedelta


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
        return self.env['hr.employee'].search([
            ('auto_generate_week', '=', True),
            ('active', '=', True),
            ('department_id', '!=', False)
        ])

    @api.model
    def _default_start_date(self):
        today = date.today()
        days_ahead = 7 - today.weekday()
        return today + timedelta(days=days_ahead)

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

    def action_generate_weeks(self):
        """Generate schedules for specified weeks"""
        if not self.employee_ids:
            return {'type': 'ir.actions.act_window_close'}

        created_records = self.env['hr.telework.day']

        for week in range(self.weeks_count):
            week_start = self.start_date + timedelta(weeks=week)

            if week_start.weekday() != 0:
                week_start = week_start - timedelta(days=week_start.weekday())

            for employee in self.employee_ids:
                if not employee.department_id:
                    continue

                if not self.override_existing:
                    existing_count = self.env['hr.telework.day'].search_count([
                        ('employee_id', '=', employee.id),
                        ('date', '>=', week_start),
                        ('date', '<', week_start + timedelta(days=7)),
                    ])
                    if existing_count >= 5:
                        continue

                if self.override_existing:
                    existing = self.env['hr.telework.day'].search([
                        ('employee_id', '=', employee.id),
                        ('date', '>=', week_start),
                        ('date', '<', week_start + timedelta(days=7)),
                    ])
                    existing.unlink()

                created = employee.generate_week_schedule(week_start)
                created_records |= created

        self._refresh_views_and_cache(created_records)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
