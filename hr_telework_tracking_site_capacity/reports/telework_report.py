# Copyright 2025 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import re
from datetime import timedelta

from odoo import api, models, fields
import logging

_logger = logging.getLogger(__name__)


class TeleworkReport(models.AbstractModel):
    _name = 'report.hr_telework_tracking_site_capacity.schedule'
    _description = 'Telework Assignments Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Get values for the report - unified table for all employees"""
        _logger.info("=== TELEWORK REPORT DEBUG ===")
        _logger.info(f"docids: {docids}")
        _logger.info(f"data: {data}")

        wizard = self.env['telework.report.wizard'].browse(docids)
        _logger.info(f"wizard: {wizard}")
        if wizard:
            _logger.info(f"wizard.date_from: {wizard.date_from}")
            _logger.info(f"wizard.date_to: {wizard.date_to}")
        else:
            _logger.info("NO WIZARD FOUND")

        if not data:
            data = {}

        # Get data from wizard
        if data.get('date_from'):
            date_from = fields.Date.from_string(data.get('date_from'))
        else:
            date_from = wizard.date_from

        if data.get('date_to'):
            date_to = fields.Date.from_string(data.get('date_to'))
        else:
            date_to = wizard.date_to

        # Get ALL declarations for the period
        all_declarations = self.env['hr.telework.day'].search([
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ])

        # Generate list of dates for the period (only business days)
        dates = []
        current_date = date_from
        while current_date <= date_to:
            # Only include business days (Monday=0 to Friday=4)
            if current_date.weekday() < 5:
                dates.append(current_date)
            current_date += timedelta(days=1)

        # Get unique employees that have declarations IN ANY MODE
        # for the selected period
        employees = all_declarations.mapped('employee_id').sorted('name')

        # Organize data by employee and date - ALL EMPLOYEES in single table
        employee_data = []
        for employee in employees:
            # Find declarations for this employee in the period
            emp_declarations = all_declarations.filtered(
                lambda d: d.employee_id == employee)
            employee_schedule = {}

            for date in dates:
                day_declaration = emp_declarations.filtered(
                    lambda d: d.date == date)
                if day_declaration:
                    decl = day_declaration[0]
                    # Show workstation for onsite, Remote for remote
                    if decl.mode == 'onsite' and decl.workstation_id:
                        # Get workstation name with only capitals and numbers
                        # Example: Moval1-001 -> M1-001
                        # CoworkingAlbatera-042 -> CA-042
                        full_name = decl.workstation_id.name
                        # Extract only uppercase letters and digits
                        workstation_short = ''.join(
                            c for c in full_name
                            if c.isupper() or c.isdigit() or c == '-'
                        )
                        # Clean up multiple consecutive hyphens
                        workstation_short = re.sub(
                            r'-+', '-', workstation_short
                        )
                        # Remove leading/trailing hyphens
                        workstation_short = workstation_short.strip('-')

                        if not workstation_short:
                            workstation_short = full_name

                        employee_schedule[date] = {
                            'workstation': workstation_short,
                            'mode': decl.mode,
                            'state': decl.state,
                        }
                    elif decl.mode == 'remote':
                        employee_schedule[date] = {
                            'workstation': 'Remote',
                            'mode': decl.mode,
                            'state': decl.state,
                        }
                    else:
                        # No workstation assigned
                        employee_schedule[date] = {
                            'workstation': 'Not assigned',
                            'mode': decl.mode,
                            'state': decl.state,
                        }
                else:
                    employee_schedule[date] = {
                        'workstation': '',
                        'mode': 'none',
                        'state': '',
                    }

            employee_data.append({
                'employee': employee,
                'schedule': employee_schedule,
            })

        _logger.info(f"Total declarations found: {len(all_declarations)}")
        _logger.info(f"Total employees found: {len(employees)}")
        _logger.info(f"Total dates: {len(dates)}")
        _logger.info(f"Employee data entries: {len(employee_data)}")
        _logger.info("=== END TELEWORK REPORT DEBUG ===")

        # Calculate office occupancy per day
        # Get all offices with workstations
        offices = self.env['office.location'].search([])
        office_occupancy = {}

        for office in offices:
            office_occupancy[office] = {}
            # Get total capacity per office (number of workstations)
            total_workstations = len(office.workstation_ids)

            for date in dates:
                # Count assignments for this office on this date
                assigned_count = len(all_declarations.filtered(
                    lambda d: d.date == date and
                    d.mode == 'onsite' and
                    d.workstation_id and
                    d.workstation_id.office_id == office
                ))

                office_occupancy[office][date] = {
                    'assigned': assigned_count,
                    'total': total_workstations,
                    'available': total_workstations - assigned_count,
                    'percentage': (
                        (assigned_count / total_workstations * 100)
                        if total_workstations > 0 else 0
                    ),
                }

        return {
            'doc_ids': docids,
            'doc_model': 'telework.report.wizard',
            'docs': wizard,
            'date_from': date_from,
            'date_to': date_to,
            'dates': dates,
            'all_declarations': all_declarations,
            'employees': employees,
            'employee_data': employee_data,
            'offices': offices,
            'office_occupancy': office_occupancy,
            'weekdays': [
                'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'
            ],
        }
