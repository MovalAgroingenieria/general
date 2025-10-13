# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    capacity_policy = fields.Selection([
            ('flexible', 'Flexible'),
            ('strict', 'Strict'),
        ],
        string='Capacity Policy',
        config_parameter='hr_telework_tracking_site_capacity.capacity_policy',
        default='flexible',
        required=True)

    cutoff_weekday = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday'),
    ], string='Cutoff Day',
        config_parameter='hr_telework_tracking_site_capacity.cutoff_weekday',
        default='3',
        help='Weekday deadline for creating declarations')

    cutoff_time = fields.Float(
        string='Cutoff Time',
        config_parameter='hr_telework_tracking_site_capacity.cutoff_time',
        default=18.0,
        help='Time deadline for creating declarations (24h format)')

    auto_confirm_weekday = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday'),
    ], string='Auto-Confirmation Day',
        config_parameter='hr_telework_tracking_site_capacity.'
                         'auto_confirm_weekday',
        default='4',
        help='Weekday for automatic confirmation')

    auto_confirm_time = fields.Float(
        string='Auto-Confirmation Time',
        config_parameter='hr_telework_tracking_site_capacity.'
                         'auto_confirm_time',
        default=8.0,
        help='Time for automatic confirmation (24h format)')

    # Simplified method for employee preferences
    def action_open_employee_preferences(self):
        """Open employee preferences tree view"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Employee Preferences',
            'res_model': 'hr.employee',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [],
            'view_id': self.env.ref(
                'hr_telework_tracking_site_capacity.'
                'view_hr_employee_telework_tree'
            ).id,
            'context': {
                'default_auto_generate_week': True,
            },
        }

    @api.model
    def can_create_declarations_for_week(self, target_week_start):
        """
        Check if declarations can be created for a specific week
        Returns True if:
        - We haven't passed this week's cutoff day/time, OR
        - The user is an HR manager
        """
        cutoff_weekday_param = self.env['ir.config_parameter'].sudo() \
            .get_param('hr_telework_tracking_site_capacity.cutoff_weekday')
        cutoff_time_param = self.env['ir.config_parameter'].sudo() \
            .get_param('hr_telework_tracking_site_capacity.cutoff_time')

        if not cutoff_weekday_param:
            return True  # If no cutoff day configured, allow

        try:
            from datetime import datetime, timedelta

            cutoff_weekday = int(cutoff_weekday_param)  # 0=Monday, 6=Sunday
            cutoff_time = float(cutoff_time_param or 18.0)

            # Calculate this week's cutoff day
            now = datetime.now()
            days_since_monday = now.weekday()  # 0=Monday, 6=Sunday

            # Calculate days until cutoff day
            days_to_cutoff = cutoff_weekday - days_since_monday
            if days_to_cutoff < 0:
                days_to_cutoff += 7  # If already passed this week, go to next

            # Create cutoff datetime
            cutoff_hour = int(cutoff_time)
            cutoff_minute = int((cutoff_time - cutoff_hour) * 60)

            cutoff_dt = now.replace(
                hour=cutoff_hour,
                minute=cutoff_minute,
                second=0,
                microsecond=0
            ) + timedelta(days=days_to_cutoff)

            # If we haven't passed the cutoff day/time, allow
            if now <= cutoff_dt:
                return True

            # If we've passed the cutoff day/time, only allow managers
            return self.env.user.has_group('hr.group_hr_manager')

        except (ValueError, TypeError):
            return True  # If there's an error, allow by default
