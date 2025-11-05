# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api


def post_init_hook(env: api.Environment):
    """
    Odoo 18+ post-init hook.

    Initializes the configuration parameter used by crm_filemgmt.
    Using sudo() because ir.config_parameter writes are restricted.
    """
    icp = env["ir.config_parameter"].sudo()
    icp.set_param("crm_filemgmt.annual_seq_prefix", "EXP")
