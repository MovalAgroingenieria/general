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

    def _get_model(self, model_name, public=False):
        """Get model, with sudo if public access."""
        if public:
            return request.env[model_name].sudo()
        return request.env[model_name]

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

    def _format_sensor_data(self, sensor, public=False):
        """Format sensor data."""
        reading_model = self._get_model(
            'mdm.measurement.device.sensor.reading', public)
        last_reading = reading_model.search([
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
        return sensor_info

    def _format_device_data(self, device, public=False):
        """Format device data."""
        sensor_data = []
        for sensor in device.sensor_ids:
            sensor_data.append(self._format_sensor_data(sensor, public))
        photo_url = None
        if not public and device.photo:
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

    def _get_devices_init_config(self, public=False):
        """Get initial configuration for devices GIS mode."""
        category_model = self._get_model(
            'mdm.measurement.device.category', public)
        device_model = self._get_model('mdm.measurement.device', public)
        categories_output = {}
        # Get categories available for GIS devices mode
        categories = category_model.search([
            ('available_for_gis_devices', '=', True),
        ], order='name asc')
        # Define domain field based on public/private mode
        device_field = ('available_for_public_gis_devices' if public
                        else 'available_for_gis_devices')
        for category in categories:
            # Count devices for this category
            device_count = device_model.search_count([
                ('category_id', '=', category.id),
                (device_field, '=', True),
            ])
            # For public mode, only include categories with devices
            if public and device_count == 0:
                continue
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

    def _get_mdm_category_devices(self, public=False):
        """Get devices for a category."""
        device_model = self._get_model('mdm.measurement.device', public)
        jsonrequest = request.jsonrequest
        params = jsonrequest.get('kwargs', {})
        category_id = params.get('category_id', False)
        limit = params.get('limit', 100)
        offset = params.get('offset', 0)
        if not category_id:
            return json.dumps(
                {'error': 'No category_id provided'}, ensure_ascii=False)
        # Define domain field based on public/private mode
        device_field = ('available_for_public_gis_devices' if public
                        else 'available_for_gis_devices')
        domain = [
            ('category_id', '=', category_id),
            (device_field, '=', True),
        ]
        # Get total count
        total_count = device_model.search_count(domain)
        # Get devices with pagination
        devices = device_model.search(
            domain,
            limit=limit,
            offset=offset,
        )
        devices_output = []
        for device in devices:
            devices_output.append(self._format_device_data(device, public))
        output = {
            'devices': devices_output,
            'total_count': total_count,
            'has_more': total_count > (offset + limit),
            'category_id': category_id,
        }
        return json.dumps(output, ensure_ascii=False)

    @http.route('/devices_init_config', auth='user', type='json',
                methods=['POST'], csrf=False)
    def get_devices_init_config(self, *args, **kwargs):
        """Get initial configuration for devices GIS mode (authenticated)."""
        return self._get_devices_init_config(public=False)

    @http.route('/mdm_category_devices', auth='user', type='json',
                methods=['POST'], csrf=False)
    def get_mdm_category_devices(self, *args, **kwargs):
        """Get devices for a category (authenticated)."""
        return self._get_mdm_category_devices(public=False)

    @http.route('/public_devices_init_config', auth='public', type='json',
                methods=['POST'], csrf=False)
    def get_public_devices_init_config(self, *args, **kwargs):
        """Get initial configuration for public devices GIS mode."""
        return self._get_devices_init_config(public=True)

    @http.route('/public_mdm_category_devices', auth='public', type='json',
                methods=['POST'], csrf=False)
    def get_public_mdm_category_devices(self, *args, **kwargs):
        """Get devices for a category visible in public viewer."""
        return self._get_mdm_category_devices(public=True)
