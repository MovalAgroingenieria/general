# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import timedelta
from odoo import api, fields, models


class TeleworkReportWizard(models.TransientModel):
    _name = 'telework.report.wizard'
    _description = 'Telework Report Wizard'

    date_from = fields.Date(
        string='From',
        required=True,
        default=lambda self: fields.Date.today()
    )

    date_to = fields.Date(
        string='To',
        required=True,
        default=lambda self: fields.Date.today() + timedelta(days=6)
    )

    office_ids = fields.Many2many(
        comodel_name='office.location',
        relation='telework_report_wizard_office_rel',
        column1='wizard_id',
        column2='office_id',
        string='Offices',
        required=False,
        domain=[('active', '=', True)],
        default=lambda self: self.env['office.location'].search([
            ('active', '=', True)
        ]),
    )

    @api.onchange('date_from')
    def _onchange_date_from(self):
        """Adjust end date when start date changes"""
        if self.date_from:
            days_ahead = 6 - self.date_from.weekday()
            self.date_to = self.date_from + timedelta(days=days_ahead)

    def action_generate_report(self):
        """Generate the PDF report for one or multiple offices."""
        self.ensure_one()

        report_action = self.env.ref(
            'hr_telework_tracking_site_capacity.'
            'action_report_telework_schedule'
        )

        offices = self.office_ids
        if not offices:
            offices = self.env['office.location'].search([
                ('active', '=', True)
            ])

        if not offices:
            return False

        data = {
            'date_from': fields.Date.to_string(self.date_from),
            'date_to': fields.Date.to_string(self.date_to),
            'office_ids': offices.ids,
        }

        return report_action.report_action(self, data=data)
