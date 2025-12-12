# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import tools

def post_load():
    from odoo.addons.hr.models.hr_employee_public import HrEmployeePublic

    def init(self):
        """Force recreate hr_employee_public view with ALL hr_employee fields."""
        # Get all stored fields from hr_employee model dynamically
        employee_model = self.env['hr.employee']
        fields_list = []

        for name, field in employee_model._fields.items():
            if field.store and field.type not in ['many2many', 'one2many', 'binary']:
                fields_list.append('emp.%s' % name)

        field_select = ','.join(fields_list)

        # Recreate the view with ALL available fields
        tools.drop_view_if_exists(self.env.cr, 'hr_employee_public')
        self.env.cr.execute("""CREATE or REPLACE VIEW hr_employee_public as (
            SELECT %s
            FROM hr_employee emp
        )""" % field_select)

        # Force registry reload to pick up new view structure
        self.env.registry.clear_caches()

    # Monkey patch the init method of the base class
    HrEmployeePublic.init = init
