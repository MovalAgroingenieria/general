# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_manufactured = fields.Boolean(
        help="Enable for products that you manufacture "
        "(used for SCRAP fee calculation).",
    )

    product_component_line_ids = fields.One2many(
        comodel_name="material.component.line",
        inverse_name="product_tmpl_id",
        string="Material Components",
    )

    # Rounded net weight in grams (derived from `weight`, which is in kilograms).
    weight_net_gram_round = fields.Float(
        string="Net Weight (g, rounded)",
        compute="_compute_weight_net_gram_round",
        store=True,
        digits=(16, 0),
        help="Product weight in grams, rounded to the"
        " nearest gram. Source: `weight` (kg).",
    )

    @api.depends("weight")
    def _compute_weight_net_gram_round(self):
        for record in self:
            kg = record.weight or 0.0  # `weight` is in kilograms on product.template
            record.weight_net_gram_round = round(kg * 1000.0)
