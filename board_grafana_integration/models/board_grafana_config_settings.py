# -*- coding: utf-8 -*-
# 2022 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api


class BoardGrafanaConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"
    _name = "board.grafana.configuration"

    grafana_url_raw = fields.Char(
        string="Grafana URL",
        required=True,
        help="The URL of grafana host.")

    grafana_url = fields.Char(
        compute="_compute_grafana_url")

    grafana_api_key = fields.Char(
        string="Grafana API Key")

    grafana_default_datasource = fields.Char(
        string="Default datasource",
        help="The default datasource.")

    grafana_dashboard_height = fields.Integer(
        string="Dashboard height",
        help="Height of dashboard, in pixels (optional).")

    grafana_dashboard_uid = fields.Char(
        string="Dashboard uid",
        help="The id of the welcome dashboard "
             "(optional, else the dashboard list will be shown).")

    @api.depends("grafana_url_raw")
    def _compute_grafana_url(self):
        for record in self:
            url = record.grafana_url_raw
            if url.endswith("/"):
                url = url.rstrip("/")
            record.grafana_url = url

    @api.multi
    def set_default_values(self):
        values = self.env["ir.values"].sudo()
        values.set_default("board.grafana.configuration",
                           "grafana_url_raw", self.grafana_url_raw)
        values.set_default("board.grafana.configuration",
                           "grafana_url", self.grafana_url)
        values.set_default("board.grafana.configuration",
                           "grafana_api_key", self.grafana_api_key)
        values.set_default("board.grafana.configuration",
                           "grafana_default_datasource",
                           self.grafana_default_datasource)
        values.set_default("board.grafana.configuration",
                           "grafana_dashboard_height",
                           self.grafana_dashboard_height)
        values.set_default("board.grafana.configuration",
                           "grafana_dashboard_uid",
                           self.grafana_dashboard_uid)
