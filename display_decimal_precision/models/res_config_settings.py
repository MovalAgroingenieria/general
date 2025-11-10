# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Example knobs you used to keep in decimal.precision:
    dp_product_price = fields.Integer(
        string="Product Price Display Digits",
        config_parameter="customer_purchase_follow_up.dp.Product Price",
        default=2,
        help="Scale (number of decimals) for displaying product prices.",
    )
    dp_product_uom = fields.Integer(
        string="Product UoM Display Digits",
        config_parameter="customer_purchase_follow_up.dp.Product Unit of Measure",
        default=2,
        help="Scale (number of decimals) for displaying product quantities.",
    )

    # Add more dp_* fields as needed for other 'application' names you used.
