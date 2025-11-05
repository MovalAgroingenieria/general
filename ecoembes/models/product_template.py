# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_manufactured = fields.Boolean(
        string="Is Manufactured",
    )

    product_component_line_ids = fields.One2many(
        comodel_name='material.component.line',
        inverse_name='product_tmpl_id',
        string='Material Components',
    )

    @api.depends("weight")
    def _compute_weight_net_gram_round(self):
        for item in self:
            item.weight_net_gram_round = round(item.weight * 1000)
