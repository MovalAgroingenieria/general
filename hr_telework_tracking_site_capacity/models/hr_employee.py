# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from datetime import date, datetime, timedelta


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    auto_generate_week = fields.Boolean(
        string='Enable automatic generation',
        default=False,
        help='Automatically generate weekly declarations based on preferences',
    )

    monday_preference = fields.Selection([
            ('remote', 'Remote Work'),
            ('onsite', 'On-site'),
            ('flexible', 'Flexible'),
        ],
        string='Monday',
        default='onsite',
    )

    tuesday_preference = fields.Selection([
            ('remote', 'Remote Work'),
            ('onsite', 'On-site'),
            ('flexible', 'Flexible'),
        ],
        string='Tuesday',
        default='onsite',
    )

    wednesday_preference = fields.Selection([
            ('remote', 'Remote Work'),
            ('onsite', 'On-site'),
            ('flexible', 'Flexible'),
        ],
        string='Wednesday',
        default='onsite',
    )

    thursday_preference = fields.Selection([
            ('remote', 'Remote Work'),
            ('onsite', 'On-site'),
            ('flexible', 'Flexible'),
        ],
        string='Thursday',
        default='onsite',
    )

    friday_preference = fields.Selection([
            ('remote', 'Remote Work'),
            ('onsite', 'On-site'),
            ('flexible', 'Flexible'),
        ],
        string='Friday',
        default='onsite',
    )

    preferred_workstation_ids = fields.Many2many(
        comodel_name='office.workstation',
        relation='employee_workstation_preference_rel',
        column1='employee_id',
        column2='workstation_id',
        string='Preferred Workstations',
        help='Workstations preferred by the employee',
    )

    primary_workstation_id = fields.Many2one(
        comodel_name='office.workstation',
        string='Primary Workstation',
        help='Default primary workstation',
    )

    telework_day_ids = fields.One2many(
        comodel_name='hr.telework.day',
        inverse_name='employee_id',
        string='Telework Days',
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

            # Skip days with full-day leaves/absences
            if self._has_full_day_leave(day_date):
                continue

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

    def _has_full_day_leave(self, check_date):
        """
        Check if employee has a full-day leave/absence on the given date.

        Args:
            check_date (date): The date to check for leaves

        Returns:
            bool: True if there's a full-day leave, False otherwise
        """
        if not self:
            return False

        Leave = self.env['hr.leave']
        datetime_start = datetime.combine(check_date, datetime.min.time())
        datetime_end = datetime.combine(check_date, datetime.max.time())

        # Search for approved leaves that cover this date
        leaves = Leave.search([
            ('employee_id', '=', self.id),
            ('state', '=', 'validate'),
            ('date_from', '<=', datetime_end),
            ('date_to', '>=', datetime_start),
        ])

        for leave in leaves:
            # Check if it's a full day leave
            # A leave is considered full-day if request_unit_half is False
            # or if it covers the entire working day
            if not leave.request_unit_half:
                # Check if the leave covers the entire day
                leave_start = leave.date_from.date()
                leave_end = leave.date_to.date()

                if leave_start <= check_date <= leave_end:
                    # Calculate the duration for this specific day
                    if leave.number_of_days >= 1.0:
                        return True

        return False

    @api.model
    def cron_generate_weekly_declarations(self, force=True):
        """
        Cron job that runs periodically to automatically generate declarations
        for next week for employees with auto_generate_week=True. Respects
        the cutoff day and time configuration defined in Settings.

        Args:
            force (bool): If True, skip cutoff time check. Default True.
        """
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

        if not force and now < cutoff_dt:
            return 0

        target_week_start = week_start_date + timedelta(days=7)
        target_week_end = target_week_start + timedelta(days=6)

        employees = self.search([('auto_generate_week', '=', True)])

        if not employees:
            return 0

        TeleworkDay = self.env['hr.telework.day']
        new_records = TeleworkDay.browse()

        for employee in employees:
            try:
                employee_ctx = employee.with_context(auto_generation=True)
                created = employee_ctx.generate_week_schedule(
                    target_week_start,
                    return_existing=False
                )
                new_records |= created
            except Exception:
                pass

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
