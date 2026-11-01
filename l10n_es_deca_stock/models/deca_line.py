# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class DecaLine(models.Model):
    _inherit = "deca.line"

    product_id = fields.Many2one(
        "product.product",
        index=True,
    )
