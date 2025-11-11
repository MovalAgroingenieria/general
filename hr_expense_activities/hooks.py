# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# pylint: disable=unused-argument

from odoo import SUPERUSER_ID, api
from odoo.tools.misc import str2bool

PARAM_OLD = "ht_expense_activities.with_activity"
PARAM_NEW = "hr_expense_activities.with_activity"


def post_init_hook(cr, registry):
    """Migrate legacy config parameter to the canonical one and remove the old key."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    icp = env["ir.config_parameter"].sudo()

    old_val = icp.get_param(PARAM_OLD, default=None)
    new_val = icp.get_param(PARAM_NEW, default=None)

    if new_val is None and old_val is not None:
        normalized = "True" if str2bool(str(old_val)) else "False"
        icp.set_param(PARAM_NEW, normalized)

    # Remove legacy key if present
    old_rec = icp.search([("key", "=", PARAM_OLD)], limit=1)
    if old_rec:
        old_rec.unlink()
