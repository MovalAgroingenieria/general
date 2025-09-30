# -*- coding: utf-8 -*-
# Copyright 2019 Solvos Consultoría Informática (<http://www.solvos.es>)
# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models, api


class StockPicking(models.Model):
    _inherit = "stock.picking"

    maintenance_request_id = fields.Many2one(
        comodel_name="maintenance.request",
        index=True,
    )

    maintenance_equipment_id = fields.Many2one(
        comodel_name="maintenance.equipment",
        related="maintenance_request_id.equipment_id",
    )

    @api.onchange('maintenance_request_id')
    def _onchange_maintenance_request_id(self):
        default_type = self.env['ir.values'].get_default(
            'maintenance.config.settings', 'default_stock_picking_type')
        if default_type:
            for record in self:
                if record.maintenance_request_id:
                    record.picking_type_id = default_type
