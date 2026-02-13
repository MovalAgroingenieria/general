# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.http import request
from odoo.addons.mdm_sensor_management_gis.controllers.mdm_gis_controller \
    import MDMGisController


class MDMGisControllerGrafana(MDMGisController):

    def _build_grafana_multisensor_url(
            self, device, sensor_type, sensor_ids):
        # Get grafana base url
        grafana_url = request.env['ir.values'].get_default(
            'board.grafana.configuration', 'grafana_url')
        if not grafana_url:
            return None
        # Get datasource
        grafana_default_datasource = request.env['ir.values'].get_default(
            'board.grafana.configuration',
            'grafana_default_datasource')
        db_name = (grafana_default_datasource
                   if grafana_default_datasource
                   else request.env.cr.dbname)
        # Get dashboard ID from settings
        dashboard_id = request.env['ir.values'].get_default(
            'mdm.config.settings',
            'gis_sensorreading_dashboard_multisensor_id')
        if not dashboard_id:
            return None
        dashboard = request.env[
            'board.grafana.dashboard.storage'].browse(dashboard_id)
        if not (dashboard and dashboard.exists() and
                dashboard.dashboard_path):
            return None
        # Build URL with parameters
        url = grafana_url + dashboard.dashboard_path
        url += '&var-datasource=' + db_name
        url += '&var-device_id=' + str(device.id)
        url += '&var-sensor_type_id=' + str(sensor_type.id)
        # Add all sensor IDs for this type
        for sensor_id in sensor_ids:
            url += '&var-sensor_ids=' + str(sensor_id)
        url += '&var-uom_id=' + str(sensor_type.uom_id.id)
        url += '&refresh=30s'
        return url

    def _format_device_data(self, device, public=False):
        device_info = super(
            MDMGisControllerGrafana, self)._format_device_data(device, public)
        # Group sensors by type and build multisensor URLs
        sensors_by_type = {}
        for sensor in device.sensor_ids:
            if sensor.type_id:
                type_id = sensor.type_id.id
                if type_id not in sensors_by_type:
                    sensors_by_type[type_id] = {
                        'sensor_type': sensor.type_id,
                        'sensor_ids': [],
                    }
                sensors_by_type[type_id]['sensor_ids'].append(sensor.id)
        # Build Grafana multisensor URLs for each type
        grafana_multisensor_urls = {}
        for type_id, type_data in sensors_by_type.items():
            sensor_type = type_data['sensor_type']
            sensor_ids = type_data['sensor_ids']
            url = self._build_grafana_multisensor_url(
                device, sensor_type, sensor_ids)
            if url:
                grafana_multisensor_urls[sensor_type.name] = url
        device_info['grafana_multisensor_urls'] = grafana_multisensor_urls
        return device_info

    def _format_sensor_data(self, sensor, public=False):
        sensor_info = super(
            MDMGisControllerGrafana, self)._format_sensor_data(sensor, public)
        # Add Grafana URLs
        sensor_info['grafana_url'] = sensor.grafana_url or ''
        sensor_info['grafana_histogram_url'] = (
            sensor.grafana_histogram_url or '')
        return sensor_info
