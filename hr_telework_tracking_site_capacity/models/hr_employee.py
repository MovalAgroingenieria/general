# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    auto_generate_week = fields.Boolean(
        string='Enable Automatic Generation',
        default=False,
        help='Automatically generate weekly telework schedule'
    )

    monday_preference = fields.Selection([
        ('remote', 'Remote Work'),
        ('onsite', 'On-site'),
        ('flexible', 'Flexible'),
    ], string='Monday', default='onsite')

    tuesday_preference = fields.Selection([
        ('remote', 'Remote Work'),
        ('onsite', 'On-site'),
        ('flexible', 'Flexible'),
    ], string='Tuesday', default='onsite')

    wednesday_preference = fields.Selection([
        ('remote', 'Remote Work'),
        ('onsite', 'On-site'),
        ('flexible', 'Flexible'),
    ], string='Wednesday', default='onsite')

    thursday_preference = fields.Selection([
        ('remote', 'Remote Work'),
        ('onsite', 'On-site'),
        ('flexible', 'Flexible'),
    ], string='Thursday', default='onsite')

    friday_preference = fields.Selection([
        ('remote', 'Remote Work'),
        ('onsite', 'On-site'),
        ('flexible', 'Flexible'),
    ], string='Friday', default='onsite')

    preferred_workstation_ids = fields.Many2many(
        'office.workstation',
        'employee_workstation_preference_rel',
        'employee_id',
        'workstation_id',
        string='Preferred Workstations',
        help='Workstations preferred by the employee')

    primary_workstation_id = fields.Many2one(
        'office.workstation',
        string='Primary Workstation',
        help='Default primary workstation')

    telework_day_ids = fields.One2many(
        'hr.telework.day',
        'employee_id',
        string='Telework Days'
    )

    def generate_week_schedule(self, monday_date=None, return_existing=True):
        """Generate weekly schedule based on employee preferences"""
        if not monday_date:
            today = date.today()
            days_ahead = 7 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            monday_date = today + timedelta(days=days_ahead)

        friday_date = monday_date + timedelta(days=4)
        existing = self.env['hr.telework.day'].search([
            ('employee_id', '=', self.id),
            ('date', '>=', monday_date),
            ('date', '<=', friday_date)
        ])

        if existing:
            return existing if return_existing else self.env['hr.telework.day']

        created_records = self.env['hr.telework.day']
        preferences = [
            self.monday_preference,
            self.tuesday_preference,
            self.wednesday_preference,
            self.thursday_preference,
            self.friday_preference
        ]

        for i, preference in enumerate(preferences):
            day_date = monday_date + timedelta(days=i)

            if self.department_id:
                mode = self._map_preference_to_mode(preference)

                day_vals = {
                    'employee_id': self.id,
                    'date': day_date,
                    'mode': mode,
                    'department_id': self.department_id.id,
                }
                if self.env.context.get('auto_generation'):
                    day_vals['source'] = 'auto_rule'
                created_records |= self.env['hr.telework.day'].create(day_vals)

        return created_records

    def _map_preference_to_mode(self, preference):
        """Convert preference to mode, flexible converts to on-site"""
        if preference == 'flexible':
            return 'onsite'
        return preference or 'onsite'

    @api.model
    def cron_generate_weekly_declarations(self, force=True):
        """
        Cron job that runs periodically to automatically generate declarations
        for next week for employees with auto_generate_week=True. Respects
        the cutoff day and time configuration defined in Settings.

        Args:
            force (bool): If True, skip cutoff time check. Default True.
        """
        _logger.info("=== GENERATE WEEKLY CRON START ===")
        Param = self.env['ir.config_parameter'].sudo()

        def _safe_int(value, default):
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        def _safe_float(value, default):
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        cutoff_weekday = _safe_int(
            Param.get_param(
                'hr_telework_tracking_site_capacity.cutoff_weekday'
            ),
            3
        )
        cutoff_time = _safe_float(
            Param.get_param('hr_telework_tracking_site_capacity.cutoff_time'),
            18.0
        )

        _logger.info(
            "Generate config: weekday=%s (0=Mon), time=%.2f",
            cutoff_weekday, cutoff_time
        )

        now = fields.Datetime.now()
        week_start_date = now.date() - timedelta(days=now.weekday())
        cutoff_date = week_start_date + timedelta(days=cutoff_weekday)

        cutoff_hour = int(cutoff_time)
        cutoff_minute = int((cutoff_time - cutoff_hour) * 60)
        cutoff_dt = datetime.combine(
            cutoff_date,
            datetime.min.time()
        ).replace(
            hour=cutoff_hour,
            minute=cutoff_minute,
            second=0,
            microsecond=0
        )

        _logger.info(
            "Current time: %s, Cutoff time: %s, Force: %s",
            now, cutoff_dt, force
        )

        if not force and now < cutoff_dt:
            _logger.info(
                "Generation SKIPPED. Current time %s is before "
                "configured cutoff %s. Use force=True to override.",
                now, cutoff_dt
            )
            return 0

        if force:
            _logger.info("Force mode enabled - skipping cutoff check")

        target_week_start = week_start_date + timedelta(days=7)
        target_week_end = target_week_start + timedelta(days=6)

        _logger.info(
            "Target week: %s to %s", target_week_start, target_week_end
        )

        employees = self.search([('auto_generate_week', '=', True)])

        _logger.info(
            "Found %d employees with auto_generate_week=True", len(employees)
        )

        if not employees:
            _logger.info(
                "Generation COMPLETED: No employees with auto-generation "
                "enabled"
            )
            return 0

        TeleworkDay = self.env['hr.telework.day']
        new_records = TeleworkDay.browse()

        for employee in employees:
            _logger.info("Generating for employee: %s", employee.name)
            try:
                employee_ctx = employee.with_context(auto_generation=True)
                created = employee_ctx.generate_week_schedule(
                    target_week_start,
                    return_existing=False
                )
                new_records |= created
            except Exception as error:
                _logger.exception(
                    "Error generating week for employee %s: %s",
                    employee.name,
                    error
                )

        assignment_summary = {
            'assigned_count': 0,
            'waiting_list_count': 0,
        }

        if new_records:
            week_records = TeleworkDay.search([
                ('date', '>=', target_week_start),
                ('date', '<=', target_week_end),
                ('source', '=', 'auto_rule')
            ])

            assignment_summary = (
                TeleworkDay._auto_assign_workstations_internal(
                    declarations=week_records,
                    notify_reviewers=True
                )
            )

            TeleworkDay._notify_managers_weekly_generation(
                target_week_start,
                new_records,
                assignment_summary
            )

        _logger.info(
            "=== GENERATE WEEKLY COMPLETED === Week %s - %s. "
            "Employees: %d, New declarations: %d, Assigned: %d, "
            "Waiting: %d, Pending review: %d",
            target_week_start,
            target_week_end,
            len(employees),
            len(new_records),
            assignment_summary.get('assigned_count', 0),
            assignment_summary.get('waiting_list_count', 0),
            assignment_summary.get('pending_review_count', 0)
        )

        return len(new_records)

    def action_generate_next_week(self):
        """Action to generate next week's schedule"""
        created_records = self.generate_week_schedule()

        if created_records:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Generated Schedule',
                'res_model': 'hr.telework.day',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', created_records.ids)],
                'context': {'default_employee_id': self.id},
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Information',
                    'message': ('Schedule for next week already exists.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
