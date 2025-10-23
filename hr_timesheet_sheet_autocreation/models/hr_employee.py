# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from datetime import date, datetime, timedelta


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def cron_generate_weekly_timesheets(self):
        """Cron job to generate weekly timesheets for all employees in Monday"""
        sheet = self.env['hr_timesheet.sheet']
        today = fields.Date.today()

        if today.weekday() != 0:
            return 0

        date_start = today
        date_end = date_start + timedelta(days=6)

        employees = self.search([('active', '=', True)])

        created_count = 0
        for employee in employees:
            # Check if timesheet already exists for this period
            existing = sheet.search([
                ('employee_id', '=', employee.id),
                ('date_start', '=', date_start),
                ('date_end', '=', date_end),
            ], limit=1)

            if existing:
                continue

            # Create timesheet
            try:
                sheet.create({
                    'employee_id': employee.id,
                    'date_start': date_start,
                    'date_end': date_end,
                    'company_id': employee.company_id.id,
                })
                created_count += 1
            except Exception:
                continue

        return created_count
