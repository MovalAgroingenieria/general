# 2023-2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    dp_product_price = fields.Integer(
        string="Product Price Display Digits",
        config_parameter="display_decimal_precision.dp.Product Price",
        default=2,
        help="Scale (number of decimals) for displaying product prices.",
    )
    dp_product_uom = fields.Integer(
        string="Product UoM Display Digits",
        config_parameter="display_decimal_precision.dp.Product Unit of Measure",
        default=2,
        help="Scale (number of decimals) for displaying product quantities.",
    )
