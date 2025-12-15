from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.cr.execute(
        """
        UPDATE decimal_precision
           SET display_digits = COALESCE(display_digits, digits, 2)
    """
    )
