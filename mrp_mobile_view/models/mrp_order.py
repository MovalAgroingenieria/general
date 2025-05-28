# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api
from datetime import date

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

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
            