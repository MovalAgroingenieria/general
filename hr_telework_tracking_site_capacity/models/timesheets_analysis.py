# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class TimesheetsAnalysisReport(models.Model):
    _inherit = 'timesheets.analysis.report'

    is_telework = fields.Boolean(
        string='Telework',
        readonly=True,
        help='Indicates if this timesheet entry was performed in '
             'telework mode',
    )

    @api.model
    def _select(self):
        """Override _select to add is_telework field"""
        select_str = super()._select()
        # Add is_telework to the SELECT clause
        select_str += """,
                A.is_telework AS is_telework"""
        return select_str
