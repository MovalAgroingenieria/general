# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from . import models
from .hooks import post_load

def post_init_hook(cr, registry):
    """Post-init hook to recreate hr_employee_public view with all fields."""
    from odoo import api, SUPERUSER_ID
    from odoo.tools import drop_view_if_exists

    env = api.Environment(cr, SUPERUSER_ID, {})

    # Get the hr_employee_public model
    model = env['hr.employee.public']

    # Drop and recreate the view with all fields
    drop_view_if_exists(cr, model._table)
    cr.execute("""CREATE or REPLACE VIEW %s as (
        SELECT
            %s
        FROM hr_employee emp
    )""" % (model._table, model._get_fields()))
