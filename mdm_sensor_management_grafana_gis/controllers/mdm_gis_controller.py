# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.addons.mdm_sensor_management_gis.controllers.mdm_gis_controller \
    import MDMGisController


class MDMGisControllerGrafana(MDMGisController):

    def _format_sensor_data(self, sensor):
        sensor_info = super(
            MDMGisControllerGrafana, self)._format_sensor_data(sensor)
        # Add Grafana URLs
        sensor_info['grafana_url'] = sensor.grafana_url or ''
        sensor_info['grafana_histogram_url'] = (
            sensor.grafana_histogram_url or '')
        return sensor_info
