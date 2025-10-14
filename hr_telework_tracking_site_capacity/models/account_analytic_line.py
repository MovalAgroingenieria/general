# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    is_telework = fields.Boolean(
        string='Telework',
        compute='_compute_is_telework',
        store=True,
        default=False,
        help='Indicates if this timesheet entry was performed in '
             'telework mode',
    )

    @api.depends('employee_id', 'date')
    def _compute_is_telework(self):
        """
        Compute if the timesheet line was done in telework mode.
        Checks if the employee has a telework declaration for that date.
        """
        for line in self:
            is_telework = False
            if line.employee_id and line.date:
                # Search for a telework declaration for this employee and date
                telework_day = self.env['hr.telework.day'].search([
                    ('employee_id', '=', line.employee_id.id),
                    ('date', '=', line.date),
                    ('mode', '=', 'remote'),
                ], limit=1)
                is_telework = bool(telework_day)
            line.is_telework = is_telework
