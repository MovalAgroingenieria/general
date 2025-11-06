# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.api import SUPERUSER_ID, Environment


def post_init_hook(cr, registry):
    env = Environment(cr, SUPERUSER_ID, {})
    env.cr.execute("UPDATE decimal_precision SET display_digits = digits;")
