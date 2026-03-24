# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from datetime import timedelta


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def cron_generate_weekly_timesheets(self):
        sheet = self.env['hr_timesheet.sheet']
        today = fields.Date.today()

        if today.weekday() != 0:
            return 0

        date_start = today
        date_end = date_start + timedelta(days=6)

        employees = self.search([
            ('active', '=', True),
            ('user_id', '!=', False),
        ])

        manager_group = self.env.ref('hr_timesheet.group_timesheet_manager', raise_if_not_found=False)
        manager_partner_ids = []
        if manager_group:
            manager_partner_ids = manager_group.users.mapped('partner_id').ids

        created_count = 0

        for employee in employees:
            existing = sheet.search([
                ('employee_id', '=', employee.id),
                ('date_start', '=', date_start),
                ('date_end', '=', date_end),
            ], limit=1)

            if existing:
                continue

            new_sheet = sheet.create({
                'employee_id': employee.id,
                'date_start': date_start,
                'date_end': date_end,
                'company_id': employee.company_id.id,
            })

            if manager_partner_ids:
                new_sheet.message_subscribe(partner_ids=manager_partner_ids)
            created_count += 1

        return created_count
