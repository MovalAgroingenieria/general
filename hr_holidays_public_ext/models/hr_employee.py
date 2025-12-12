# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, tools


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    def _register_hook(self):
        super()._register_hook()
        self.init()

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        # Get all stored fields from hr.employee
        employee_fields = self.env['hr.employee']._fields
        select_fields = []

        for name, field in employee_fields.items():
            if field.store and field.type not in ['one2many', 'many2many']:
                select_fields.append(f'"{name}"')

        fields_str = ', '.join(select_fields)

        self.env.cr.execute("""
            CREATE or REPLACE VIEW %s as (
                SELECT
                    %s
                FROM
                    hr_employee
            )
        """ % (self._table, fields_str))

        # Clear cache to ensure new fields are recognized
        self.env.registry.clear_cache()
