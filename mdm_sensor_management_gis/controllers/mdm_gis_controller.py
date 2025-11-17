# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import http
from odoo.http import request
import json
import re
import unicodedata


class MDMGisController(http.Controller):

    def to_valid_variable_name(self, s):
        """Convert string to valid variable name."""
        if isinstance(s, str):
            s = s.decode('utf-8')
        s = unicodedata.normalize('NFD', s)
        s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
        s = re.sub(ur'[^a-zA-Z0-9_ ]', u'', s)
        s = re.sub(ur'\s+', u'_', s)
        if re.match(ur'^[0-9]', s):
            s = u'_' + s
        return s.encode('utf-8')

    def _get_geojson_from_device(self, device):
        # Check if base_wua module is installed
        # (provides with_gis_measurement_device field)
        if (hasattr(device, 'with_gis_measurement_device') and
                device.with_gis_measurement_device):
            # Get the geometry as GeoJSON
            request.env.cr.execute("""
                SELECT ST_AsGeoJSON(geom)
                FROM mdm_gis_measurement_device
                WHERE name = %s
            """, (device.name,))
            result = request.env.cr.fetchone()
            if result and result[0]:
                return json.loads(result[0])
        return None

    def _get_config_for_devices_mode(self):
        refresh_interval = request.env['ir.values'].get_default(
            'mdm.config.settings',
            'default_gis_devices_refresh_interval') or 60
        return {
            'default_interval': refresh_interval * 1000,
        }

    def _format_device_data(self, device):
        # Get latest sensor readings
        sensor_data = []
        for sensor in device.sensor_ids:
            # Get last reading
            last_reading = request.env[
                'mdm.measurement.device.sensor.reading'].search([
                    ('sensor_id', '=', sensor.id),
                ], limit=1, order='measurement_time desc')
            sensor_info = {
                'id': sensor.id,
                'name': sensor.name,
                'sensor_type': (sensor.type_id.name
                                if sensor.type_id else ''),
                'last_value': last_reading.value if last_reading else None,
                'last_date': last_reading.measurement_time if last_reading else
                None,
                'uom': sensor.uom_id.name if sensor.uom_id else '',
            }
            sensor_data.append(sensor_info)
        photo_url = None
        if device.photo:
            photo_url = '/web/image/mdm.measurement.device/%s/photo' % (
                device.id)
        return {
            'id': device.id,
            'name': device.name,
            'category': device.category_id.name if device.category_id else '',
            'category_id': (device.category_id.id
                            if device.category_id else False),
            'geometry': self._get_geojson_from_device(device),
            'photo_url': photo_url,
            'sensors': sensor_data,
        }

    @http.route('/devices_init_config', auth='user', type='json',
                methods=['POST'], csrf=False)
    def get_devices_init_config(self, *args, **kwargs):
        """Get initial configuration for devices GIS mode."""
        categories_output = {}
        # Get categories available for GIS devices mode
        categories = request.env['mdm.measurement.device.category'].search([
            ('available_for_gis_devices', '=', True),
        ], order='name asc')
        for category in categories:
            # Count devices for this category
            device_count = request.env['mdm.measurement.device'].search_count([
                ('category_id', '=', category.id),
                ('available_for_gis_devices', '=', True),
            ])
            geojson_style = '{}'
            if category.geojson_style:
                geojson_style = category.geojson_style.replace(
                    '\n', '').strip()
            legend_symbology = ''
            if category.legend_symbology:
                legend_symbology = category.legend_symbology.replace(
                    '\n', '').strip()
            categories_output[self.to_valid_variable_name(category.name)] = {
                'id': category.id,
                'name': category.name,
                'geojson_style': geojson_style,
                'legend_symbology': legend_symbology,
                'device_count': device_count,
            }
        output = {
            'config': self._get_config_for_devices_mode(),
            'categories': categories_output,
        }
        return json.dumps(output, ensure_ascii=False)

    @http.route('/mdm_category_devices', auth='user', type='json',
                methods=['POST'], csrf=False)
    def get_mdm_category_devices(self, *args, **kwargs):
        jsonrequest = request.jsonrequest
        params = jsonrequest.get('kwargs', {})
        category_id = params.get('category_id', False)
        limit = params.get('limit', 100)
        offset = params.get('offset', 0)
        if not category_id:
            return json.dumps(
                {'error': 'No category_id provided'}, ensure_ascii=False)
        domain = [
            ('category_id', '=', category_id),
            ('available_for_gis_devices', '=', True),
        ]
        # Get total count
        total_count = request.env['mdm.measurement.device'].search_count(
            domain)
        # Get devices with pagination
        devices = request.env['mdm.measurement.device'].search(
            domain,
            limit=limit,
            offset=offset,
        )
        devices_output = []
        for device in devices:
            devices_output.append(self._format_device_data(device))
        output = {
            'devices': devices_output,
            'total_count': total_count,
            'has_more': total_count > (offset + limit),
            'category_id': category_id,
        }
        return json.dumps(output, ensure_ascii=False)
