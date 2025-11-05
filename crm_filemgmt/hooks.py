# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.api import Environment, SUPERUSER_ID


def post_init_hook(cr, registry):
    env = Environment(cr, SUPERUSER_ID, {})
    # Parameter initialization
    env['ir.config_parameter'].set_param(
        'crm_filemgmt.annual_seq_prefix', 'EXP')
