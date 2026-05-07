# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
import json
import math
from datetime import datetime

import werkzeug

from odoo import http, fields
from odoo.http import request


def _parse_dt(value):
    """Parse an ISO-like timestamp from query string. Returns datetime."""
    if not value:
        return fields.Datetime.from_string(fields.Datetime.now())
    try:
        return fields.Datetime.from_string(value)
    except (TypeError, ValueError):
        try:
            # Accept also full ISO with 'T'.
            return datetime.strptime(
                value.replace('T', ' ').split('.')[0],
                '%Y-%m-%d %H:%M:%S')
        except (TypeError, ValueError):
            return fields.Datetime.from_string(fields.Datetime.now())


def _parse_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_json_loads(value, default=None):
    try:
        return json.loads(value) if value else default
    except (TypeError, ValueError):
        return default


class MeteoController(http.Controller):
    """HTTP endpoints for the meteo viewer.

    TODO[Phase 4]: add /public_meteo_* variants gated by a per-product
    public flag.
    """

    @http.route('/meteo/get_raster_urls', type='json',
                auth='user', methods=['POST'])
    def get_raster_urls(self, product_id=None, from_t=None, to_t=None,
                        **kwargs):
        """Return a list of raster descriptors for a time range.

        One round-trip replaces the N individual /meteo/get_raster calls
        the viewer would need for prefetch. The response is a list sorted
        by timestamp, with each item containing the info needed by the
        viewer to decide whether to download:

          [{ts, url, raster_id, version_hash, state, warnings}]

        Items whose state != 'done' are included so the viewer knows
        not to bother fetching those timestamps. The viewer then fetches
        the actual bytes only for cache-misses using /meteo/get_raster.
        """
        product_id = _parse_int(product_id)
        if not product_id:
            return {'error': 'missing_params'}
        product_model = request.env['meteo.product']
        product = product_model.browse(product_id)
        if not product.exists():
            return {'error': 'unknown_product'}
        from_dt = _parse_dt(from_t)
        to_dt = _parse_dt(to_t)
        if from_dt > to_dt:
            from_dt, to_dt = to_dt, from_dt
        from_str = fields.Datetime.to_string(from_dt)
        to_str = fields.Datetime.to_string(to_dt)
        raster_model = request.env['meteo.raster']
        rasters = raster_model.search([
            ('product_id', '=', product.id),
            ('valid_from', '>=', from_str),
            ('valid_from', '<=', to_str),
        ], order='valid_from asc')
        base_url = request.httprequest.host_url.rstrip('/')
        result = []
        for r in rasters:
            ts_iso = fields.Datetime.to_string(
                fields.Datetime.from_string(r.valid_from),
            ) if r.valid_from else None
            url = (
                '%s/meteo/get_raster?product_id=%s&t=%s' % (
                    base_url,
                    product.id,
                    werkzeug.urls.url_quote(ts_iso or ''),
                )
            ) if r.state == 'done' and r.cog_attachment_id else None
            result.append({
                'ts': ts_iso,
                'url': url,
                'raster_id': r.id,
                'version_hash': r.product_version_hash,
                'state': r.state,
                'method': r.method,
                'n_stations': r.n_stations_used,
                'warnings': json.loads(r.warnings_json or '[]'),
            })
        return {'product_id': product_id, 'frames': result}

    @http.route('/meteo/init_config', type='json',
                auth='user', methods=['POST'])
    def init_config(self, **kwargs):
        product_model = request.env['meteo.product']
        products = product_model.search([('active', '=', True)])
        result = []
        for p in products:
            result.append({
                'id': p.id,
                'name': p.name,
                'srs': p.srs,
                'extent': [p.extent_xmin, p.extent_ymin,
                           p.extent_xmax, p.extent_ymax],
                'variable': {
                    'id': p.variable_id.id,
                    'code': p.variable_id.code,
                    'name': p.variable_id.name,
                    'min_value': p.variable_id.min_value,
                    'max_value': p.variable_id.max_value,
                    'color_ramp': _safe_json_loads(
                        p.variable_id.color_ramp,
                        default=None,
                    ),
                    'uom': (p.variable_id.uom_id.name
                            if p.variable_id.uom_id else None),
                },
                'aggregation': p.aggregation,
                'terrain_correction': p.terrain_correction,
                'lapse_rate_c_per_km': p.lapse_rate_c_per_km,
                'slider_back_minutes': p.history_minutes,
                'slider_step_minutes': p.step_minutes,
                'timezone': p.timezone or 'Europe/Madrid',
            })
        return {'products': result}

    @http.route('/meteo/get_raster', type='http',
                auth='user', methods=['GET'])
    def get_raster(self, product_id=None, t=None, **kwargs):
        product_id = _parse_int(product_id)
        if not product_id:
            return request.not_found()
        product_model = request.env['meteo.product']
        product = product_model.browse(product_id)
        if not product.exists():
            return request.not_found()
        target_dt = _parse_dt(t)
        raster_model = request.env['meteo.raster']
        raster = raster_model.get_or_create(product, target_dt)
        if raster.state != 'done' or not raster.cog_attachment_id:
            payload = {
                'error': raster.error_message or 'no_data',
                'state': raster.state,
                'n_stations': raster.n_stations_used or 0,
                'warnings': json.loads(raster.warnings_json or '[]'),
            }
            return werkzeug.wrappers.Response(
                json.dumps(payload),
                status=503,
                content_type='application/json')
        att = raster.cog_attachment_id
        meta_headers = [
            ('Content-Type', 'image/tiff'),
            ('Content-Disposition',
             'inline; filename="%s"' % (att.datas_fname or 'raster.tif')),
            ('X-Meteo-Raster-Id', str(raster.id)),
            ('X-Meteo-Stations', str(raster.n_stations_used)),
            ('X-Meteo-Method', raster.method or ''),
            ('X-Meteo-Compute-Ms', str(raster.compute_ms or 0)),
            ('Access-Control-Expose-Headers',
             'Content-Length,Content-Range,'
             'X-Meteo-Raster-Id,X-Meteo-Stations,'
             'X-Meteo-Method,X-Meteo-Compute-Ms'),
        ]
        cog_bytes = base64.b64decode(att.datas)
        return request.make_response(cog_bytes, headers=meta_headers)

    @http.route('/meteo/stations', type='json',
                auth='user', methods=['POST'])
    def stations(self, product_id=None, t=None, **kwargs):
        """Return the stations that actually contributed to the raster
        at time `t`, in EPSG:4326 (lon/lat) so the viewer can drop
        Leaflet markers directly without a client-side reprojection.

        Reads the snapshot stored on `meteo.raster.stations_json` so
        the markers shown on the map exactly match the inputs of the
        interpolation (a station with no reading inside the time window
        was not used and will not appear). If the raster does not yet
        exist (or predates the snapshot field), falls back to a live
        query that uses the same SQL collector as the compute pipeline.
        """
        product_id = _parse_int(product_id)
        if not product_id:
            return {'error': 'missing_params'}
        product_model = request.env['meteo.product']
        product = product_model.browse(product_id)
        if not product.exists():
            return {'error': 'unknown_product'}
        target_dt = _parse_dt(t)
        target_str = fields.Datetime.to_string(target_dt)
        raster_model = request.env['meteo.raster']
        raster = raster_model.search([
            ('product_id', '=', product.id),
            ('valid_from', '<=', target_str),
            ('valid_to', '>=', target_str),
            ('state', '=', 'done'),
            ('product_version_hash', '=', product.version_hash),
        ], limit=1, order='valid_from desc')
        snapshot = None
        if raster and raster.stations_json:
            try:
                snapshot = json.loads(raster.stations_json)
            except (ValueError, TypeError):
                snapshot = None
        if snapshot is None:
            snapshot = request.env['meteo.raster'].collect_stations(
                product, target_dt)
        # Strip the SRS coords; the viewer only needs lon/lat.
        stations = [{
            'name': s.get('name'),
            'lon': s.get('lon'),
            'lat': s.get('lat'),
            'value': s.get('value'),
            'measurement_time': s.get('measurement_time'),
        } for s in snapshot
            if s.get('lon') is not None and s.get('lat') is not None]
        return {
            'stations': stations,
            'unit': (product.variable_id.uom_id.name
                     if product.variable_id.uom_id else None),
        }

    @http.route('/meteo/explain_point', type='json',
                auth='user', methods=['POST'])
    def explain_point(self, product_id=None, t=None,
                      x=None, y=None, **kwargs):
        product_id = _parse_int(product_id)
        x = _parse_float(x)
        y = _parse_float(y)
        if not (product_id and x is not None and y is not None):
            return {'error': 'missing_params'}
        product_model = request.env['meteo.product']
        product = product_model.browse(product_id)
        if not product.exists():
            return {'error': 'unknown_product'}
        target_dt = _parse_dt(t)
        # Re-use the SQL station collector to get the same set the
        # raster was built with.
        stations = request.env['meteo.raster'].collect_stations(
            product, target_dt)
        if not stations:
            return {'error': 'no_data'}
        contributions = []
        eps = 1e-9
        power = product.idw_power or 2.0
        weights_sum = 0.0
        value_sum = 0.0
        for s in stations:
            sx, sy, sv = s['x'], s['y'], s['value']
            d = math.sqrt((sx - x) ** 2 + (sy - y) ** 2)
            w = 1.0 / ((d ** power) + eps)
            weights_sum += w
            value_sum += w * sv
            contributions.append({
                'station': s['name'],
                'value': sv,
                'distance_m': d,
                'weight_raw': w,
            })
        # Normalise weights for display.
        for c in contributions:
            c['weight'] = c.pop('weight_raw') / weights_sum
        contributions.sort(key=lambda c: c['distance_m'])
        return {
            'value': value_sum / weights_sum,
            'unit': (product.variable_id.uom_id.name
                     if product.variable_id.uom_id else None),
            'method': 'idw',
            'method_specific': {
                'kind': 'idw',
                'data': {'p': power},
            },
            'contributions': contributions[:10],
        }
