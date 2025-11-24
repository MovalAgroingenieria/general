# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MDMConfigSettings(models.TransientModel):
    _inherit = 'mdm.config.settings'

    default_gis_devices_refresh_interval = fields.Integer(
        string='GIS Devices Refresh Interval (seconds)',
        default=60,
        help='Default refresh interval for device information in GIS viewer',
    )

    @api.model
    def get_default_gis_devices_refresh_interval(self, fields_list):
        return {
            'default_gis_devices_refresh_interval':
                self.env['ir.values'].get_default(
                    'mdm.config.settings',
                    'default_gis_devices_refresh_interval') or 60,
        }

    @api.multi
    def set_default_gis_devices_refresh_interval(self):
        self.ensure_one()
        self.env['ir.values'].sudo().set_default(
            'mdm.config.settings',
            'default_gis_devices_refresh_interval',
            self.default_gis_devices_refresh_interval,
        )
