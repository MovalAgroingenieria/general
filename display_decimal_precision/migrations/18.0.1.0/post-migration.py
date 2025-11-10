# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# pylint: disable=broad-exception-caught

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Migrate decimal_precision data to ir.config_parameter if table exists."""
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Check the table; in v18 it likely doesn't exist, so guard with try/except.
    try:
        cr.execute("SELECT name, display_digits FROM decimal_precision")
        rows = cr.fetchall()
    except Exception:  # table missing or dropped in previous upgrades
        rows = []

    if not rows:
        return

    icp = env["ir.config_parameter"].sudo()
    for name, display_digits in rows:
        if not name:
            continue
        key = f"customer_purchase_follow_up.dp.{name}"
        # Prefer display_digits; if null, fall back to 2
        scale = display_digits if isinstance(display_digits, int) else 2
        icp.set_param(key, str(scale))
