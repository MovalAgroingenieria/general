# -*- coding: utf-8 -*-
# 2026 Moval Agroingenieria
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
import calendar
import json
import logging
import time
from datetime import datetime, timedelta

import requests

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

AVAMET_MAGNITUDES = [
    'temp_min',
    'temp_avg',
    'temp_max',
    'humidity_min',
    'humidity_avg',
    'humidity_max',
    'pressure_min',
    'pressure_avg',
    'pressure_max',
    'wind_direction',
    'wind_avg',
    'wind_gust',
    'rain',
]

WIND_DIRECTION_TO_DEGREES = {
    'N': 0.0,
    'NNE': 22.5,
    'NE': 45.0,
    'ENE': 67.5,
    'E': 90.0,
    'ESE': 112.5,
    'SE': 135.0,
    'SSE': 157.5,
    'S': 180.0,
    'SSW': 202.5,
    'SW': 225.0,
    'WSW': 247.5,
    'W': 270.0,
    'WNW': 292.5,
    'NW': 315.0,
    'NNW': 337.5,
}

DEFAULT_WEATHERLINK_BASE_URL = 'https://api.weatherlink.com/v2'
DEFAULT_WEATHERLINK_RETRIES = 3
DEFAULT_WEATHERLINK_TIMEOUT = 25
DEFAULT_WEATHERLINK_CONNECT_TIMEOUT = 8
DEFAULT_WEATHERLINK_CHUNK_SECONDS = 6 * 60 * 60
DEFAULT_WEATHERLINK_BACKOFF = 1.5

WEATHERLINK_MAGNITUDE_KEY_CANDIDATES = {
    'temp_min': ['temp_min', 'temp_lo', 'temp_low', 'day_temp_lo'],
    'temp_avg': ['temp_avg', 'temp', 'temp_out', 'air_temp'],
    'temp_max': ['temp_max', 'temp_hi', 'temp_high', 'day_temp_hi'],
    'humidity_min': ['hum_min', 'hum_lo', 'day_hum_lo'],
    'humidity_avg': ['humidity_avg', 'hum', 'hum_out', 'humidity', 'hum_last'],
    'humidity_max': ['hum_max', 'hum_hi', 'day_hum_hi'],
    'pressure_min': ['bar_min', 'pressure_min', 'bar_lo'],
    'pressure_avg': ['bar', 'bar_abs', 'bar_sea_level', 'pressure'],
    'pressure_max': ['bar_max', 'pressure_max', 'bar_hi'],
    'wind_direction': [
        'wind_dir',
        'wind_dir_scalar_avg',
        'wind_dir_of_prevail',
    ],
    'wind_avg': ['wind_speed_avg', 'wind_speed', 'wind_speed_last'],
    'wind_gust': ['wind_gust', 'wind_speed_hi'],
    'rain': [
        'rainfall_daily',
        'rainfall',
        'rainfall_last_15_min',
        'rain_24_hr',
        'rainfall_mm',
        'rainfall_in',
        'rainfall_clicks',
    ],
}

AVAMET_MEASUREMENT_PREFIXES = (
    'bar_',
    'cooling_degree_days',
    'dew_point_',
    'et',
    'heat_index_',
    'heating_degree_days',
    'hum_',
    'rain',
    'solar_',
    'temp_',
    'thsw_index_',
    'thw_index_',
    'uv_',
    'wet_bulb_',
    'wind_',
)

AVAMET_IGNORED_FIELD_NAMES = set([
    'afc',
    'arch_int',
    'bgn',
    'bluetooth_version',
    'bootloader_version',
    'dns_type_used',
    'error_packets',
    'espressif_version',
    'firmware_version',
    'good_packets_streak',
    'health_version',
    'input_voltage',
    'ip_address_type',
    'ip_v4_address',
    'ip_v4_gateway',
    'ip_v4_netmask',
    'link_uptime',
    'local_api_queries',
    'network_error',
    'network_type',
    'radio_version',
    'rain_size',
    'rapid_records_sent',
    'reception',
    'resynchs',
    'rssi',
    'rx_bytes',
    'solar_rad_volt_last',
    'solar_volt_last',
    'supercap_volt_last',
    'touchpad_wakeups',
    'trans_battery',
    'trans_battery_flag',
    'ts',
    'tx_bytes',
    'tx_id',
    'tz_offset',
    'uptime',
    'uv_volt_last',
    'wifi_rssi',
])

AVAMET_IGNORED_FIELD_SUFFIXES = (
    '_at',
    '_flag',
    '_version',
)


class RemoteControl(models.Model):
    _inherit = 'remotecontrol'

    is_avamet = fields.Boolean(
        string='Is AVAMET',
        default=False,
        readonly=True,
    )

    @api.multi
    def action_open_avamet_import_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'avamet_import',
            'name': _('AVAMET Import'),
            'target': 'current',
            'context': {
                'remotecontrol_id': self.id,
                'remotecontrol_name': self.name or '',
            },
        }

    @api.multi
    def _avamet_http_get(self, endpoint, params=None, timeout=None):
        self.ensure_one()
        cfg = self._avamet_get_connection_params()
        api_key = (cfg.get('api_key') or '').strip()
        api_secret = (cfg.get('api_secret') or '').strip()
        if not api_key or not api_secret:
            raise ValueError('Missing WeatherLink API credentials.')
        base_url = (self.base_url or '').strip()
        if 'weatherlink.com' not in base_url:
            base_url = DEFAULT_WEATHERLINK_BASE_URL
        base_url = base_url.rstrip('/')
        url = '%s/%s' % (base_url, endpoint.lstrip('/'))
        query_params = dict(params or {})
        query_params['api-key'] = api_key
        connect_timeout = int(
            cfg.get('connect_timeout') or DEFAULT_WEATHERLINK_CONNECT_TIMEOUT,
        )
        read_timeout = int(
            timeout or
            cfg.get('request_timeout') or
            DEFAULT_WEATHERLINK_TIMEOUT,
        )
        retries = int(
            cfg.get('request_retries') or DEFAULT_WEATHERLINK_RETRIES,
        )
        backoff = float(
            cfg.get('request_backoff') or DEFAULT_WEATHERLINK_BACKOFF,
        )

        last_error = None
        for attempt in range(retries + 1):
            try:
                response = requests.get(
                    url,
                    params=query_params,
                    headers={'x-api-secret': api_secret},
                    timeout=(connect_timeout, read_timeout),
                )
                if response.status_code in [429, 500, 502, 503, 504]:
                    last_error = ValueError(
                        'HTTP %s' % response.status_code,
                    )
                    if attempt < retries:
                        time.sleep(backoff * (attempt + 1))
                        continue
                response.raise_for_status()
                return response.json() or {}
            except (
                requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
                requests.exceptions.HTTPError,
                ValueError,
            ) as error:
                last_error = error
                if attempt < retries:
                    time.sleep(backoff * (attempt + 1))
                    continue
                raise last_error

        raise last_error

    @api.model
    def _avamet_get_connection_params(self):
        cfg = {}
        try:
            cfg = json.loads(self.connection_params or '{}')
        except Exception:
            cfg = {}
        if not isinstance(cfg, dict):
            cfg = {}
        return cfg

    @api.model
    def _avamet_extract_station_id(self, station):
        station_id = ''
        for key in ['station_id', 'stationId', 'did', 'id', 'uuid']:
            if station.get(key) is not None and station.get(key) != '':
                station_id = station.get(key)
                break
        station_id = u'%s' % (station_id or u'')
        station_id = station_id.strip()
        return station_id

    @api.model
    def _avamet_extract_station_name(self, station):
        station_name = ''
        for key in ['station_name', 'name', 'private_name', 'public_name']:
            if station.get(key) is not None and station.get(key) != '':
                station_name = station.get(key)
                break
        station_name = u'%s' % (station_name or u'')
        station_name = station_name.strip()
        return station_name

    @api.multi
    def avamet_fetch_station_catalog(self):
        self.ensure_one()
        payload = {}
        try:
            payload = self._avamet_http_get('stations', timeout=45)
        except Exception as error:
            _logger.warning(
                '[AVAMET] WeatherLink catalog fetch failed: %s',
                error,
            )
            payload = {}

        api_stations = payload.get('stations') or payload.get('data') or []
        if isinstance(api_stations, dict):
            api_stations = list(api_stations.values())

        stations = []
        known_ids = set()
        for station in api_stations:
            if not isinstance(station, dict):
                continue
            station_id = self._avamet_extract_station_id(station)
            station_name = self._avamet_extract_station_name(station)
            if station_id and station_id not in known_ids:
                stations.append({
                    'station_id': station_id,
                    'name': station_name or station_id,
                })
                known_ids.add(station_id)

        return stations

    @api.multi
    def avamet_fetch_station_metadata(self, station_id):
        self.ensure_one()
        metadata = {}
        try:
            payload = self._avamet_http_get(
                'stations/%s' % station_id,
                timeout=45,
            )
            station = {}
            if (
                isinstance(payload.get('stations'), list) and
                payload.get('stations')
            ):
                station = payload.get('stations')[0]
            elif isinstance(payload.get('data'), list) and payload.get('data'):
                station = payload.get('data')[0]
            elif isinstance(payload, dict):
                station = payload

            municipality = (
                station.get('city') or station.get('region_name') or ''
            ).strip()
            province = (
                station.get('region') or station.get('state') or ''
            ).strip()
            if municipality:
                metadata['Municipio'] = municipality
            if province:
                metadata['Provincia'] = province
            for key in [
                'station_name',
                'name',
                'timezone',
                'station_id',
                'did',
            ]:
                value = station.get(key)
                if value:
                    metadata[key] = '%s' % value
        except Exception as error:
            _logger.warning(
                '[AVAMET] WeatherLink station metadata failed for %s: %s',
                station_id,
                error,
            )
        return metadata

    @api.model
    def _avamet_should_expose_field(self, field_name, raw_value):
        if not field_name:
            return False
        if raw_value is None:
            return False
        if isinstance(raw_value, (dict, list, tuple)):
            return False
        if field_name in AVAMET_IGNORED_FIELD_NAMES:
            return False
        for suffix in AVAMET_IGNORED_FIELD_SUFFIXES:
            if field_name.endswith(suffix):
                return False
        for prefix in AVAMET_MEASUREMENT_PREFIXES:
            if field_name.startswith(prefix):
                return True
        return False

    @api.model
    def _avamet_field_to_label(self, field_name):
        labels = {
            'bar_absolute':        _('Absolute Pressure'),
            'bar_hi':              _('Pressure High'),
            'bar_lo':              _('Pressure Low'),
            'bar_sea_level':       _('Sea Level Pressure'),
            'cooling_degree_days': _('Cooling Degree Days'),
            'dew_point_hi':        _('Dew Point High'),
            'dew_point_in':        _('Indoor Dew Point'),
            'dew_point_last':      _('Dew Point'),
            'dew_point_lo':        _('Dew Point Low'),
            'et':                  _('Evapotranspiration'),
            'heat_index_hi':       _('Heat Index High'),
            'heat_index_in':       _('Indoor Heat Index'),
            'heat_index_last':     _('Heat Index'),
            'heating_degree_days': _('Heating Degree Days'),
            'hum_hi':              _('Relative Humidity High'),
            'hum_in_hi':           _('Indoor Humidity High'),
            'hum_in_last':         _('Indoor Humidity'),
            'hum_in_lo':           _('Indoor Humidity Low'),
            'hum_last':            _('Relative Humidity'),
            'hum_lo':              _('Relative Humidity Low'),
            'rain_rate_hi_clicks': _('Rain Rate High (pulses)'),
            'rain_rate_hi_in':     _('Rain Rate High (in)'),
            'rain_rate_hi_mm':     _('Rain Rate High'),
            'rainfall_clicks':     _('Rainfall (pulses)'),
            'rainfall_in':         _('Rainfall (in)'),
            'rainfall_mm':         _('Rainfall'),
            'solar_energy':        _('Solar Energy'),
            'solar_rad_avg':       _('Solar Radiation Average'),
            'solar_rad_hi':        _('Solar Radiation High'),
            'temp_avg':            _('Temperature Average'),
            'temp_hi':             _('Temperature High'),
            'temp_in_hi':          _('Indoor Temperature High'),
            'temp_in_last':        _('Indoor Temperature'),
            'temp_in_lo':          _('Indoor Temperature Low'),
            'temp_last':           _('Temperature'),
            'temp_lo':             _('Temperature Low'),
            'thsw_index_hi':       _('THSW Index High'),
            'thsw_index_last':     _('THSW Index'),
            'thsw_index_lo':       _('THSW Index Low'),
            'thw_index_hi':        _('THW Index High'),
            'thw_index_last':      _('THW Index'),
            'thw_index_lo':        _('THW Index Low'),
            'uv_dose':             _('UV Dose'),
            'uv_index_avg':        _('UV Index Average'),
            'uv_index_hi':         _('UV Index High'),
            'wet_bulb_hi':         _('Wet Bulb High'),
            'wet_bulb_last':       _('Wet Bulb'),
            'wet_bulb_lo':         _('Wet Bulb Low'),
            'wind_chill_last':     _('Wind Chill'),
            'wind_chill_lo':       _('Wind Chill Low'),
            'wind_dir_of_prevail': _('Prevailing Wind Direction'),
            'wind_run':            _('Wind Run'),
            'wind_speed_avg':      _('Wind Speed Average'),
            'wind_speed_hi':       _('Wind Speed High'),
            'wind_speed_hi_dir':   _('Wind Direction at Max Speed'),
        }
        label = labels.get(field_name)
        if label:
            return label
        return (field_name or '').replace('_', ' ').strip().title()

    @api.model
    def _avamet_guess_uom(self, field_name):
        uom_name = 'AVAMET Unknown'
        short_name = '?'
        if field_name.startswith('hum_'):
            uom_name = 'AVAMET Percent'
            short_name = '%'
        elif field_name.startswith('wind_dir') or field_name.endswith('_dir'):
            uom_name = 'AVAMET Degrees'
            short_name = 'deg'
        elif field_name.endswith('_mm'):
            uom_name = 'AVAMET mm'
            short_name = 'mm'
        return {
            'name': uom_name,
            'short_name': short_name,
        }

    @api.multi
    def avamet_fetch_station_variables(self, station_id, value_date=None):
        self.ensure_one()
        value_date = value_date or fields.Date.from_string(
            fields.Date.today(),
        )
        start_ts = self._avamet_day_to_timestamp(value_date)
        end_ts = self._avamet_day_to_timestamp(
            value_date + timedelta(days=1),
        )
        variables = {}
        payload_keys = set()
        for chunk_start, chunk_end in self._avamet_iter_time_chunks(
            start_ts,
            end_ts,
        ):
            try:
                payload = self._avamet_http_get(
                    'historic/%s' % station_id,
                    params={
                        'start-timestamp': chunk_start,
                        'end-timestamp': chunk_end,
                    },
                    timeout=20,
                )
            except Exception as error:
                _logger.error(
                    '[AVAMET] HTTP request failed for station %s: %s',
                    station_id,
                    error,
                )
                raise
            if not payload:
                continue
            payload_keys.update(payload.keys())
            sensors = payload.get('sensors') or []
            for sensor in sensors:
                data_points = sensor.get('data') or []
                for record in data_points:
                    if not isinstance(record, dict):
                        continue
                    for field_name, raw_value in record.items():
                        if not self._avamet_should_expose_field(
                            field_name,
                            raw_value,
                        ):
                            continue
                        variable = variables.get(field_name)
                        if not variable:
                            guessed_uom = self._avamet_guess_uom(field_name)
                            variable = {
                                'api_field': field_name,
                                'sensor_name': self._avamet_field_to_label(
                                    field_name,
                                ),
                                'sample_value': '',
                                'uom_name': guessed_uom['name'],
                                'uom_short_name': guessed_uom['short_name'],
                            }
                            variables[field_name] = variable
                        if variable['sample_value'] == '':
                            variable['sample_value'] = u'%s' % raw_value
        if not variables and payload_keys:
            _logger.warning(
                '[AVAMET] No variables found for station %s after '
                'filtering. Payload keys: %s',
                station_id,
                list(payload_keys),
            )
        if not variables:
            _logger.warning(
                '[AVAMET] No variables found for station %s on %s',
                station_id,
                value_date,
            )
            return []
        sorted_variables = variables.values()
        sorted_variables.sort(
            key=lambda entry: (
                entry.get('sensor_name') or '',
                entry.get('api_field') or '',
            ),
        )
        return sorted_variables

    @api.model
    def _avamet_to_float(self, raw_value):
        if raw_value is None:
            return None
        if isinstance(raw_value, (int, long, float)):
            return float(raw_value)
        value = None
        normalized = (raw_value or '').strip()
        if normalized in ('', '-', '--'):
            value = None
        else:
            if ',' in normalized and '.' in normalized:
                normalized = normalized.replace('.', '').replace(',', '.')
            elif ',' in normalized:
                normalized = normalized.replace(',', '.')
            try:
                value = float(normalized)
            except Exception:
                value = None
        return value

    @api.model
    def _avamet_extract_record_value(self, record, field_key):
        value = None
        field_name = None
        raw_value = None
        if field_key in record:
            raw_value = record.get(field_key)
            field_name = field_key
        else:
            candidate_fields = WEATHERLINK_MAGNITUDE_KEY_CANDIDATES.get(
                field_key,
                [],
            )
            for candidate in candidate_fields:
                if candidate in record:
                    raw_value = record.get(candidate)
                    field_name = candidate
                    break
        if raw_value is None:
            return value, field_name
        if field_key == 'wind_direction' or field_name in [
            'wind_dir',
            'wind_dir_scalar_avg',
        ]:
            if isinstance(raw_value, basestring):
                cardinal = (raw_value or '').strip().upper()
                value = WIND_DIRECTION_TO_DEGREES.get(cardinal)
            else:
                value = self._avamet_to_float(raw_value)
        else:
            value = self._avamet_to_float(raw_value)
        return value, field_name

    @api.model
    def _avamet_iter_dicts(self, node):
        if isinstance(node, dict):
            yield node
            for value in node.values():
                for child in self._avamet_iter_dicts(value):
                    yield child
        elif isinstance(node, list):
            for value in node:
                for child in self._avamet_iter_dicts(value):
                    yield child

    @api.model
    def _avamet_get_aggregation_mode(self, field_key):
        if field_key == 'rain':
            return 'rain_total'
        if field_key.startswith('rain_rate'):
            return 'max'
        if field_key.startswith('rainfall') or field_key.startswith('rain_'):
            return 'rain_total'
        if (
            field_key.endswith('_min') or
            field_key.endswith('_lo') or
            '_lo_' in field_key
        ):
            return 'min'
        if (
            field_key.endswith('_max') or
            field_key.endswith('_hi') or
            '_hi_' in field_key
        ):
            return 'max'
        return 'avg'

    @api.model
    def _avamet_day_to_timestamp(self, value_date):
        day_start = datetime(
            value_date.year,
            value_date.month,
            value_date.day,
            0,
            0,
            0,
        )
        return int(calendar.timegm(day_start.timetuple()))

    @api.model
    def _avamet_iter_time_chunks(self, start_ts, end_ts):
        chunk_seconds = DEFAULT_WEATHERLINK_CHUNK_SECONDS
        chunk_start = start_ts
        while chunk_start < end_ts:
            chunk_end = min(end_ts, chunk_start + chunk_seconds)
            yield chunk_start, chunk_end
            chunk_start = chunk_end

    @api.model
    def _avamet_aggregate_day_values(self, field_key, day_values):
        if not day_values:
            return None
        values = [entry[0] for entry in day_values]
        aggregation_mode = self._avamet_get_aggregation_mode(field_key)
        if aggregation_mode == 'min':
            return min(values)
        if aggregation_mode == 'max':
            return max(values)
        if aggregation_mode == 'rain_total':
            daily_values = [
                entry[0] for entry in day_values
                if 'daily' in (entry[1] or '').lower()
            ]
            if daily_values:
                return max(daily_values)
            return sum(values)
        return sum(values) / float(len(values))

    @api.multi
    def avamet_fetch_sensor_points(self, station_id, field_key,
                                   start_date, end_date):
        self.ensure_one()
        points = []
        day_cursor = start_date
        while day_cursor <= end_date:
            day_values = []
            day_errors = []
            start_ts = self._avamet_day_to_timestamp(day_cursor)
            end_ts = self._avamet_day_to_timestamp(
                day_cursor + timedelta(days=1),
            )
            for chunk_start, chunk_end in self._avamet_iter_time_chunks(
                start_ts,
                end_ts,
            ):
                try:
                    payload = self._avamet_http_get(
                        'historic/%s' % station_id,
                        params={
                            'start-timestamp': chunk_start,
                            'end-timestamp': chunk_end,
                        },
                        timeout=20,
                    )
                    for record in self._avamet_iter_dicts(payload):
                        value, field_name = self._avamet_extract_record_value(
                            record,
                            field_key,
                        )
                        if value is not None:
                            day_values.append((value, field_name))
                except Exception as error:
                    day_errors.append('%s' % error)
            if day_errors and not day_values:
                _logger.warning(
                    '[AVAMET] WeatherLink historic unavailable for '
                    'station=%s day=%s field=%s (%s errors). '
                    'Last error: %s',
                    station_id,
                    day_cursor,
                    field_key,
                    len(day_errors),
                    day_errors[-1],
                )
            day_value = self._avamet_aggregate_day_values(
                field_key,
                day_values,
            )
            if day_value is not None:
                points.append({
                    'measurement_time': day_cursor.strftime(
                        '%Y-%m-%d 12:00:00',
                    ),
                    'value': day_value,
                })
            day_cursor += timedelta(days=1)
        return points

    @api.multi
    def avamet_get_sensor_plan(self, selected_device_ids=None):
        self.ensure_one()
        selected_device_ids = selected_device_ids or []
        if selected_device_ids:
            devices = self.env['mdm.measurement.device'].search([
                ('id', 'in', selected_device_ids),
                ('remotecontrol_id', '=', self.id),
            ])
        else:
            devices = self.env['mdm.measurement.device'].search([
                ('remotecontrol_id', '=', self.id),
            ])
        all_sensor_ids = []
        for device in devices:
            for sensor in device.sensor_ids:
                all_sensor_ids.append(sensor.id)
        last_readings_map = {}
        if all_sensor_ids:
            self.env.cr.execute(
                'SELECT DISTINCT ON (sensor_id) sensor_id, measurement_time '
                'FROM mdm_measurement_device_sensor_reading '
                'WHERE sensor_id IN %s AND active = TRUE '
                'ORDER BY sensor_id, measurement_time DESC',
                (tuple(all_sensor_ids),),
            )
            for sensor_id, measurement_time in self.env.cr.fetchall():
                last_readings_map[sensor_id] = measurement_time
        today_date = fields.Date.from_string(fields.Date.today())
        default_end_date = today_date - timedelta(days=1)
        default_start_date = default_end_date
        plan = []
        for device in devices:
            device_cfg = {}
            try:
                device_cfg = json.loads(device.remotecontrol_params or '{}')
            except Exception:
                device_cfg = {}
            station_id = (device_cfg.get('station_id') or '').strip()
            if not station_id:
                continue
            device_start = device_cfg.get('start_date') or ''
            for sensor in device.sensor_ids:
                sensor_cfg = {}
                try:
                    sensor_cfg = json.loads(
                        sensor.remotecontrol_params or '{}',
                    )
                except Exception:
                    sensor_cfg = {}
                field_key = (
                    sensor_cfg.get('api_field') or
                    sensor_cfg.get('magnitude') or
                    ''
                ).strip()
                if not field_key:
                    continue
                start_date = default_start_date
                last_reading_time = last_readings_map.get(sensor.id)
                if last_reading_time:
                    try:
                        start_date = fields.Datetime.from_string(
                            last_reading_time,
                        ).date()
                    except Exception:
                        start_date = default_start_date
                else:
                    raw_start = sensor_cfg.get('start_date') or device_start
                    if raw_start:
                        try:
                            start_date = fields.Date.from_string(raw_start)
                        except Exception:
                            start_date = default_start_date
                end_date = default_end_date
                if end_date < start_date:
                    end_date = start_date
                plan.append({
                    'device_id': device.id,
                    'sensor_id': sensor.id,
                    'station_id': station_id,
                    'field_key': field_key,
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                })
        return plan

    @api.multi
    def avamet_sync_sensor_plan(self, plan):
        self.ensure_one()
        total_upserts = 0
        total_errors = 0
        items = []
        for entry in plan:
            sensor_id = entry.get('sensor_id')
            station_id = entry.get('station_id')
            field_key = entry.get('field_key')
            start_date = fields.Date.from_string(entry.get('start_date'))
            end_date = fields.Date.from_string(entry.get('end_date'))
            sensor_upserts = 0
            sensor_errors = 0
            points_found = 0
            errors = []
            try:
                points = self.avamet_fetch_sensor_points(
                    station_id=station_id,
                    field_key=field_key,
                    start_date=start_date,
                    end_date=end_date,
                )
                points_found = len(points)
                for point in points:
                    try:
                        with self.env.cr.savepoint():
                            self.upsert(
                                'mdm.measurement.device.sensor.reading',
                                {
                                    'sensor_id': sensor_id,
                                    'measurement_time': (
                                        point['measurement_time']
                                    ),
                                },
                                {
                                    'value': point['value'],
                                    'remotecontrol_origin_id': self.id,
                                },
                            )
                        sensor_upserts += 1
                    except Exception as error:
                        sensor_errors += 1
                        errors.append(str(error))
            except Exception as error:
                sensor_errors += 1
                errors.append(str(error))
            total_upserts += sensor_upserts
            total_errors += sensor_errors
            items.append({
                'sensor_id': sensor_id,
                'station_id': station_id,
                'field_key': field_key,
                'start_date': entry.get('start_date'),
                'end_date': entry.get('end_date'),
                'points_found': points_found,
                'upserts': sensor_upserts,
                'errors': sensor_errors,
                'error_messages': errors,
            })
        audit = {
            'executed_at': fields.Datetime.now(),
            'total_sensors': len(plan),
            'total_upserts': total_upserts,
            'total_errors': total_errors,
            'items': items,
        }
        audit_json = json.dumps(audit, ensure_ascii=True, indent=2)
        audit_binary = base64.b64encode(audit_json.encode('utf-8'))
        audit_name = 'avamet_sync_%s.json' % fields.Datetime.now().replace(
            ':', '').replace('-', '').replace(' ', '_')
        attachment = self.env['ir.attachment'].create({
            'name': audit_name,
            'datas_fname': audit_name,
            'datas': audit_binary,
            'mimetype': 'application/json',
            'res_model': 'remotecontrol',
            'res_id': self.id,
        })
        self.message_post(
            body=u'[AVAMET] upserts=%s errors=%s' % (
                total_upserts,
                total_errors,
            ),
            attachment_ids=[attachment.id],
        )
        audit['attachment_id'] = attachment.id
        return audit
