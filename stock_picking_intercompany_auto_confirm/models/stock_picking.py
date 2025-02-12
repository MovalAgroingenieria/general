# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api


class PackageType(models.Model):
    _inherit = 'stock.picking'

    is_internal_company = fields.Boolean(
        string="Is Internal Company",
        related='partner_id.is_internal_company',
    )

    def action_update_confirm_picking(self):
        purchase_order = self.move_ids.filtered(
            lambda x: x.purchase_line_id.order_id).purchase_line_id.order_id
        intercompany_sale_order_id = purchase_order.intercompany_sale_order_id
        sale_intercompany_picking_id = self.sudo().search(
            [('sale_id', '=', intercompany_sale_order_id.id)])
        if sale_intercompany_picking_id:
            picking_to_upd = self.sudo().browse(
                sale_intercompany_picking_id.id)
            picking_to_upd.sudo().write({'move_line_ids': [(5, 0, 0)]})
            for move_line in self.move_line_ids:
                if not move_line.lot_name and not move_line.lot_id:
                    self.write({'move_line_ids': [(2, move_line.id, 0)]})
                else:
                    if move_line.lot_name:
                        lot_id = self.env['stock.lot'].sudo().search(
                            [('name', '=', move_line.lot_name),
                             ('company_id', '=',
                              picking_to_upd.company_id.id),
                             ('product_id', '=', move_line.product_id.id)])
                        if lot_id:
                            new_lot = lot_id
                        else:
                            new_lot = self.env['stock.lot'].sudo().create({
                                'name': move_line.lot_name,
                                'product_id': move_line.product_id.id,
                                'company_id': picking_to_upd.company_id.id,
                            })
                    else:
                        lot_id_my_company = self.env['stock.lot'].search(
                            [('name', '=', move_line.lot_id.name),
                             ('company_id', '=', picking_to_upd.company_id.id),
                             ('product_id', '=', move_line.product_id.id)])
                if lot_id_my_company:
                    new_lot = lot_id_my_company
                else:
                    new_lot = self.env['stock.lot'].sudo().create({
                        'name': move_line.lot_id.name,
                        'product_id': move_line.product_id.id,
                        'company_id': picking_to_upd.company_id.id,
                    })
                vals = {
                    'product_id': move_line.product_id.id,
                    'product_uom_id': move_line.product_uom_id.id,
                    'qty_done': move_line.qty_done,
                    'location_id': picking_to_upd.sudo().location_id.id,
                    'location_dest_id': picking_to_upd.sudo().location_dest_id.id,
                    'picking_id': picking_to_upd.sudo().id,
                    'lot_id': new_lot.sudo().id,
                }
                self.env['stock.move.line'].sudo().create(vals)
            picking_to_upd.sudo().button_validate()
        return True

    @api.model
    def create(self, vals):
        partner = self.env['res.partner'].search(
            [('id', '=', vals['partner_id'])])
        if partner.is_internal_company:
            picking_type = self.env['stock.picking.type'].search(
                [('intercompany_operations', '=', True),
                 ('company_id', '=', vals['company_id'])])
            vals['picking_type_id'] = picking_type.id
        return super().create(vals)


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    intercompany_operations = fields.Boolean(
        string='Intercompany Operations',
        default=False,
    )
    