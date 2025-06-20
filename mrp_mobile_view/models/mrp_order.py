# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import date

from odoo import api, fields, models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    product_drying_id = fields.Many2one(
        'product.product', 'Product',
        domain="""[
                ('type', 'in', ['product', 'consu']),
                '|',
                    ('company_id', '=', False),
                    ('company_id', '=', company_id)
            ]
            """,
        compute='_compute_product_id', store=True, copy=True, precompute=True,
        readonly=True, required=True, check_company=True,
        states={'draft': [('readonly', False)]})

    def generate_automatic_production_lot(self):
        today = date.today()
        day_number = str(today.isoweekday())
        week_number = str(date.today().isocalendar()[1]).zfill(2)
        last_year_digit = str(today.year)[-1]
        lot_name = 'S' + day_number + week_number + last_year_digit
        lot_model = self.env['stock.lot']
        for move in self.move_line_ids:
            product = move.product_id
            existing_lot = lot_model.search([
                ('name', '=', lot_name),
                ('product_id', '=', product.id),
            ], limit=1)
            if existing_lot:
                lot_id = existing_lot
            else:
                lot_id = lot_model.create({
                    'name': lot_name,
                    'product_id': move.product_id.id,
            })
            move.lot_id = lot_id
        return True

    @api.onchange('product_drying_id')
    def _onchange_product_drying_id(self):
        if self.product_drying_id:
            self.product_id = self.product_drying_id
            
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_drying_id = self.product_id
