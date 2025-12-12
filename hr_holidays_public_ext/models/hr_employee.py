# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    @api.model
    def _get_fields(self):
        """
        Override to fetch fields directly from the database table.
        This ensures that all columns present in hr_employee are included in the view,
        regardless of whether they are defined in the hr.employee.public model or not.
        """
        self.env.cr.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'hr_employee'
            ORDER BY ordinal_position
        """)
        columns = [row[0] for row in self.env.cr.fetchall()]
        return ','.join('emp."%s"' % col for col in columns)
