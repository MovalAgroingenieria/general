# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import models, fields, api


class MaintenanceSettings(models.TransientModel):
    _inherit = 'maintenance.config.settings'

    default_stock_picking_type = fields.Many2one(
        string='Default Stock Picking Type',
        comodel_name='stock.picking.type',
    )

    @api.multi
    def set_default_values(self):
        values = self.env['ir.values'].sudo()
        values.set_default('maintenance.config.settings',
                           'default_stock_picking_type',
                           self.default_stock_picking_type.id)
        # Call parent's set_default_values if it exists
        parent_method = getattr(
            super(MaintenanceSettings, self), 'set_default_values', None,
        )
        if parent_method:
            parent_method()
