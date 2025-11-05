# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    scrap_contribution_total = fields.Float(
        string="Total SCRAP Contribution (€)",
        compute="_compute_scrap_contribution_total",
        store=False,
        digits=(16, 6),
    )

    @api.depends('invoice_line_ids.product_id', 'invoice_line_ids.quantity')
    def _compute_scrap_contribution_total(self):
        for move in self:
            total = 0.0
            for line in move.invoice_line_ids:
                product = line.product_id
                if not product or not product.product_tmpl_id.is_manufactured:
                    continue

                tmpl_id = product.product_tmpl_id.id
                components = self.env['material.component.line'].search([
                    ('product_tmpl_id', '=', tmpl_id)
                ])

                for component in components:
                    fee = component.submaterial_type_id.fee_per_kg or 0.0
                    total += (component.weight_grams / 1000.0) * fee * \
                        line.quantity

            move.scrap_contribution_total = total
