# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    # Mirror of customer_payment_mode_id, stored for search/grouping.
    # Using a related avoids a custom compute method.
    computed_customer_payment_mode_id = fields.Many2one(
        comodel_name="account.payment.mode",
        related="customer_payment_mode_id",
        store=True,
        readonly=True,
    )
