# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Stores/reads from ir.config_parameter automatically
    # (string <-> bool handled by Odoo)
    with_activity = fields.Boolean(
        string="Create an activity for new expenses",
        config_parameter="hr_expense_activities.with_activity",
        default=False,
    )
