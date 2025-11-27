# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models, fields, api


class MeasurementDeviceSensor(models.Model):
    _inherit = 'mdm.measurement.device.sensor'

    grafana_url = fields.Char(
        string='Grafana Dashboard URL',
        compute='_compute_grafana_url',
        readonly=True,
    )

    grafana_histogram_url = fields.Char(
        string='Grafana Histogram URL',
        compute='_compute_grafana_histogram_url',
        readonly=True,
    )

    def _compute_grafana_url_generic(self, sensor, dashboard_setting):
        # Get grafana base url
        grafana_url = self.env['ir.values'].get_default(
            'board.grafana.configuration', 'grafana_url')
        if not grafana_url:
            return None
        # Get datasource
        grafana_default_datasource = self.env['ir.values'].get_default(
            'board.grafana.configuration',
            'grafana_default_datasource')
        db_name = (grafana_default_datasource
                   if grafana_default_datasource
                   else self.env.cr.dbname)
        # Get dashboard ID from settings
        dashboard_id = self.env['ir.values'].get_default(
            'mdm.config.settings', dashboard_setting)
        if not dashboard_id:
            return None
        dashboard = self.env[
            'board.grafana.dashboard.storage'].browse(dashboard_id)
        if not (dashboard and dashboard.exists() and
                dashboard.dashboard_path):
            return None
        # Build URL with all parameters
        url = grafana_url + dashboard.dashboard_path
        url += '&var-datasource=' + db_name
        url += '&var-sensor_id=' + str(sensor.id)
        url += '&var-sensor_name=' + sensor.name
        if sensor.device_id:
            url += '&var-device_id=' + str(sensor.device_id.id)
            url += '&var-device_name=' + sensor.device_id.name
        if sensor.uom_id:
            url += '&var-uom_id=' + str(sensor.uom_id.id)
            url += '&var-uom_name=' + sensor.uom_id.name
        url += '&refresh=30s'
        return url

    @api.multi
    def _compute_grafana_url(self):
        for sensor in self:
            sensor.grafana_url = self._compute_grafana_url_generic(
                sensor, 'gis_sensorreading_dashboard_id')

    @api.multi
    def _compute_grafana_histogram_url(self):
        for sensor in self:
            sensor.grafana_histogram_url = self._compute_grafana_url_generic(
                sensor, 'gis_sensorreading_dashboard_histogram_id')
