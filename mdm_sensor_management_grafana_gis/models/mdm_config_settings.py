# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MDMConfigSettings(models.TransientModel):
    _inherit = 'mdm.config.settings'

    gis_sensorreading_dashboard_id = fields.Many2one(
        string='GIS Sensorreading dashboard',
        comodel_name='board.grafana.dashboard.storage',
        ondelete='restrict',
    )

    gis_sensorreading_dashboard_histogram_id = fields.Many2one(
        string='GIS Sensorreading Histogram dashboard',
        comodel_name='board.grafana.dashboard.storage',
        ondelete='restrict',
    )

    @api.multi
    def set_default_values(self):
        values = self.env["ir.values"].sudo()
        values.set_default(
            "mdm.config.settings",
            "gis_sensorreading_dashboard_id",
            self.gis_sensorreading_dashboard_id.id)
        values.set_default(
            "mdm.config.settings",
            "gis_sensorreading_dashboard_histogram_id",
            self.gis_sensorreading_dashboard_histogram_id.id)
