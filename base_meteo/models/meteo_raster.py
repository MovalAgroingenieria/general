# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
import json
import logging
import os
import subprocess
import tempfile
import time
from datetime import datetime, timedelta
import pytz
from psycopg2 import IntegrityError

import numpy as np
from PIL import Image

try:
    from scipy.spatial import cKDTree
except ImportError:
    cKDTree = None

from odoo import api, exceptions, fields, models, _

_logger = logging.getLogger(__name__)

# SQL aggregation operators allowed for meteo.product.aggregation. We map
# the user-facing code to a fixed SQL expression. No string from the user
# ever reaches the SQL text.
_AGG_SQL = {
    'avg': 'AVG(r.value)',
    'sum': 'SUM(r.value)',
    'min': 'MIN(r.value)',
    'max': 'MAX(r.value)',
    # 'last' is handled with a window query, see _query_station_values.
}


class MeteoRaster(models.Model):
    _name = 'meteo.raster'
    _description = 'Meteorological Raster'
    _order = 'valid_from desc, id desc'
    _rec_name = 'display_name'

    _sql_constraints = [
        (
            'meteo_raster_product_valid_from_uniq',
            'unique(product_id, valid_from)',
            'A raster already exists for this product and timestamp.',
        ),
    ]

    @api.model
    def _get_product_tz(self, product):
        tz_name = (product.timezone or '').strip() or 'UTC'
        if pytz is None:
            return None
        try:
            return pytz.timezone(tz_name)
        except Exception:
            _logger.warning(
                'meteo: unknown timezone %r for product %s, '
                'falling back to UTC', tz_name, product.id)
            return pytz.utc

    @api.model
    def _align_target_dt(self, product, target_dt):
        """Align target_dt to the canonical slot start for product."""
        step = max(int(product.step_minutes or 0), 1)
        if step >= 1440 and pytz is not None:
            tz = self._get_product_tz(product) or pytz.utc
            local_dt = pytz.utc.localize(target_dt).astimezone(tz)
            local_midnight = local_dt.replace(
                hour=0, minute=0, second=0, microsecond=0)
            return local_midnight.astimezone(pytz.utc).replace(tzinfo=None)
        epoch = datetime(1970, 1, 1)
        elapsed_seconds = int((target_dt - epoch).total_seconds())
        step_seconds = step * 60
        slot_seconds = (elapsed_seconds // step_seconds) * step_seconds
        return epoch + timedelta(seconds=slot_seconds)

    @api.model
    def _slot_bounds(self, product, target_dt):
        """Return (slot_start, slot_end_exclusive) for target_dt."""
        slot_start = self._align_target_dt(product, target_dt)
        step = max(int(product.step_minutes or 0), 1)
        if step >= 1440 and pytz is not None:
            tz = self._get_product_tz(product) or pytz.utc
            local_start = pytz.utc.localize(slot_start).astimezone(tz)
            local_end = local_start + timedelta(minutes=step)
            slot_end = local_end.astimezone(pytz.utc).replace(tzinfo=None)
            return slot_start, slot_end
        return slot_start, slot_start + timedelta(minutes=step)

    @api.model
    def collect_stations(self, product, target_dt):
        """Return station dicts contributing to (product, target_dt).

        Each item: {name, x, y, lon, lat, value, measurement_time}
          - x,y in the product SRS (interpolator input).
          - lon,lat in EPSG:4326 (viewer markers).
        """
        cr = product.env.cr
        srs = product.srs or 'EPSG:3857'
        try:
            srs_epsg = int(srs.split(':')[-1])
        except (ValueError, AttributeError):
            raise exceptions.UserError(_(
                'Unsupported SRS %s. Use EPSG:NNNN.') % srs)
        t_lower, t_to = self._slot_bounds(product, target_dt)

        sensor_type_ids = tuple(product.variable_id.sensor_type_ids.ids) \
            or (0,)
        excluded_device_ids = tuple(product.excluded_device_ids.ids) or (0,)
        aggregation = product.aggregation or 'avg'
        if aggregation not in _AGG_SQL and aggregation != 'last':
            raise exceptions.UserError(_(
                'Unsupported aggregation method: %s') % aggregation)
        # Spatial filter: only stations whose geometry falls inside the
        # product extent. The extent is in product.srs, so we build a bbox
        # geometry in that SRS and use ST_Intersects on the device geom
        # (which PostGIS reprojects implicitly with ST_Transform).
        extent_xmin = product.extent_xmin
        extent_ymin = product.extent_ymin
        extent_xmax = product.extent_xmax
        extent_ymax = product.extent_ymax
        # 'last' uses LATERAL to pick the most recent reading per device.
        # The other aggregations use a plain GROUP BY with the SQL operator
        # from the static dict above.
        if aggregation == 'last':
            sql = """
                SELECT g.name AS device_name,
                       ST_X(ST_Transform(g.geom, %s)) AS x,
                       ST_Y(ST_Transform(g.geom, %s)) AS y,
                       ST_X(ST_Transform(g.geom, 4326)) AS lon,
                       ST_Y(ST_Transform(g.geom, 4326)) AS lat,
                       sub.value, sub.measurement_time
                FROM mdm_gis_measurement_device g
                JOIN mdm_measurement_device d ON d.name = g.name
                JOIN LATERAL (
                    SELECT r.value, r.measurement_time
                    FROM mdm_measurement_device_sensor s
                    JOIN mdm_measurement_device_sensor_reading r
                        ON r.sensor_id = s.id
                    WHERE s.device_id = d.id
                      AND s.type_id IN %s
                                            AND r.measurement_time >= %s
                                            AND r.measurement_time < %s
                      AND r.active = true
                    ORDER BY r.measurement_time DESC
                    LIMIT 1
                ) sub ON true
                WHERE g.geom IS NOT NULL
                  AND d.id NOT IN %s
                  AND ST_Intersects(
                      ST_Transform(g.geom, %s),
                      ST_MakeEnvelope(%s, %s, %s, %s, %s))
            """
            params = (srs_epsg, srs_epsg, sensor_type_ids,
                      t_lower, t_to, excluded_device_ids,
                      srs_epsg,
                      extent_xmin, extent_ymin,
                      extent_xmax, extent_ymax, srs_epsg)
        else:
            op = _AGG_SQL[aggregation]
            sql = """
                SELECT g.name AS device_name,
                       ST_X(ST_Transform(g.geom, %%s)) AS x,
                       ST_Y(ST_Transform(g.geom, %%s)) AS y,
                       ST_X(ST_Transform(g.geom, 4326)) AS lon,
                       ST_Y(ST_Transform(g.geom, 4326)) AS lat,
                       %s AS value,
                       MAX(r.measurement_time) AS measurement_time
                FROM mdm_gis_measurement_device g
                JOIN mdm_measurement_device d ON d.name = g.name
                JOIN mdm_measurement_device_sensor s ON s.device_id = d.id
                JOIN mdm_measurement_device_sensor_reading r
                    ON r.sensor_id = s.id
                WHERE s.type_id IN %%s
                                    AND r.measurement_time >= %%s
                                    AND r.measurement_time < %%s
                  AND r.active = true
                  AND g.geom IS NOT NULL
                  AND d.id NOT IN %%s
                  AND ST_Intersects(
                      ST_Transform(g.geom, %%s),
                      ST_MakeEnvelope(%%s, %%s, %%s, %%s, %%s))
                GROUP BY g.name, g.geom
            """ % (op,)
            params = (srs_epsg, srs_epsg, sensor_type_ids,
                      t_lower, t_to, excluded_device_ids,
                      srs_epsg,
                      extent_xmin, extent_ymin,
                      extent_xmax, extent_ymax, srs_epsg)
        cr.execute(sql, params)
        rows = cr.fetchall()
        out = []
        for name, x, y, lon, lat, value, ts in rows:
            if value is None:
                continue
            out.append({
                'name': name,
                'x': float(x),
                'y': float(y),
                'lon': float(lon),
                'lat': float(lat),
                'value': float(value),
                'measurement_time': (
                    fields.Datetime.to_string(ts)
                    if isinstance(ts, datetime)
                    else (ts or None)),
            })
        return out

    display_name = fields.Char(
        string='Name',
        compute='_compute_meteo_display_name',
        store=True,
    )

    product_id = fields.Many2one(
        comodel_name='meteo.product',
        string='Product',
        required=True,
        ondelete='cascade',
        index=True,
    )

    valid_from = fields.Datetime(
        string='Valid From',
        required=True,
    )

    valid_to = fields.Datetime(
        string='Valid To',
        required=True,
    )

    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('done', 'Done'),
            ('failed', 'Failed'),
        ],
        string='State',
        default='draft',
        readonly=True,
        index=True,
    )

    method = fields.Selection(
        selection=[
            ('none', 'No data'),
            ('constant', 'Constant (1 station)'),
            ('idw', 'IDW (all stations)'),
            ('idw_knn', 'IDW (k-NN)'),
        ],
        string='Method',
        readonly=True,
    )

    n_stations_used = fields.Integer(
        string='Stations Used',
        readonly=True,
    )

    grid_w = fields.Integer(
        string='Grid Width (px)',
        readonly=True,
    )

    grid_h = fields.Integer(
        string='Grid Height (px)',
        readonly=True,
    )

    compute_ms = fields.Integer(
        string='Compute Time (ms)',
        readonly=True,
    )

    cog_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string='COG File',
        readonly=True,
        ondelete='set null',
    )

    cog_size_kb = fields.Float(
        string='COG Size (kB)',
        compute='_compute_cog_size_kb',
        store=True,
    )

    warnings_json = fields.Text(
        string='Warnings',
        readonly=True,
    )

    error_message = fields.Text(
        string='Error',
        readonly=True,
    )

    parameters_json = fields.Text(
        string='Parameters Used',
        readonly=True,
        help='JSON dump of the actual parameters used for this run.',
    )

    stations_json = fields.Text(
        string='Stations Snapshot',
        readonly=True,
        help='JSON list of the stations that contributed to this '
             'raster (name, lon, lat, value, measurement_time). '
             'Used by the viewer to render markers that exactly match '
             'the inputs of the interpolation, with no recomputation.',
    )

    product_version_hash = fields.Char(
        string='Product Version Hash',
        readonly=True,
        help='Snapshot of meteo.product.version_hash at compute time.',
    )

    is_stale = fields.Boolean(
        string='Stale',
        compute='_compute_is_stale',
        search='_search_is_stale',
        help='True when the product version_hash has changed after '
             'this raster was generated.',
    )

    @api.depends('product_id', 'valid_from')
    def _compute_meteo_display_name(self):
        for record in self:
            if record.product_id and record.valid_from:
                record.display_name = '%s @ %s' % (
                    record.product_id.name, record.valid_from)
            else:
                record.display_name = _('New raster')

    @api.depends('cog_attachment_id', 'cog_attachment_id.file_size')
    def _compute_cog_size_kb(self):
        for record in self:
            if record.cog_attachment_id and \
                    record.cog_attachment_id.file_size:
                record.cog_size_kb = \
                    record.cog_attachment_id.file_size / 1024.0
            else:
                record.cog_size_kb = 0.0

    @api.depends('product_version_hash', 'product_id.version_hash')
    def _compute_is_stale(self):
        for record in self:
            record.is_stale = bool(
                record.product_version_hash and
                record.product_id and
                record.product_id.version_hash !=
                record.product_version_hash)

    def _search_is_stale(self, operator, value):
        # Materialize via SQL because the field depends on a related
        # comparison; ORM cannot push it down.
        truthy = (operator == '=' and value) or \
                 (operator == '!=' and not value)
        self.env.cr.execute("""
            SELECT r.id
            FROM meteo_raster r
            JOIN meteo_product p ON p.id = r.product_id
            WHERE r.product_version_hash IS NOT NULL
              AND r.product_version_hash <> p.version_hash
        """)
        ids = [row[0] for row in self.env.cr.fetchall()]
        return [('id', 'in' if truthy else 'not in', ids)]

    # Public entry point.
    @api.multi
    def action_compute(self):
        for record in self:
            record._compute_one()

    @api.model
    def get_or_create(self, product, target_dt):
        """Return an existing fresh raster for (product, target_dt) or
        create + compute a new one.

        "Fresh" means:
          - state == 'done'
          - product_version_hash matches current product.version_hash
          - target_dt is within [valid_from, valid_to]
        """
        target_dt = target_dt if isinstance(target_dt, datetime) else \
            fields.Datetime.from_string(target_dt)
        slot_start, slot_end = self._slot_bounds(product, target_dt)
        target_str = fields.Datetime.to_string(slot_start)
        domain = [
            ('product_id', '=', product.id),
            ('valid_from', '=', target_str),
        ]
        record = self.search(domain, limit=1, order='id desc')
        if not record:
            valid_to = slot_end - timedelta(seconds=1)
            try:
                record = self.create({
                    'product_id': product.id,
                    'valid_from': target_str,
                    'valid_to': fields.Datetime.to_string(valid_to),
                })
            except IntegrityError:
                self.env.cr.rollback()
                record = self.search(domain, limit=1, order='id desc')
        if record.state == 'done' and \
                record.product_version_hash == product.version_hash:
            return record
        record._compute_one()
        return record

    # Cron entry points.
    @api.model
    def cron_prerender(self, batch_size=200):
        """Pre-render rasters for products with is_prerendered=True.

        For each eligible product, walk the timeline from `now` back to
        `now - history_minutes` in steps of
        `step_minutes` and generate any missing or stale
        timestep. The total number of timesteps processed across all
        products in one cron run is capped by `batch_size` so the
        transaction stays bounded; subsequent runs continue where this
        one stopped (the next missing timesteps are picked again).
        """
        product_model = self.env['meteo.product']
        products = product_model.search([
            ('active', '=', True),
            ('is_prerendered', '=', True),
        ])
        now = fields.Datetime.from_string(fields.Datetime.now())
        budget = max(int(batch_size or 0), 1)
        results = []
        for product in products:
            if budget <= 0:
                break
            step = max(int(product.step_minutes or 0), 1)
            back = max(int(product.history_minutes or 0), step)
            anchor = self._align_target_dt(product, now)
            n_steps = back // step
            for i in range(n_steps + 1):
                if budget <= 0:
                    break
                t = anchor - timedelta(minutes=step * i)
                # Skip if a fresh raster already covers this timestep.
                t_str = fields.Datetime.to_string(t)
                existing = self.search([
                    ('product_id', '=', product.id),
                    ('valid_from', '=', t_str),
                    ('state', '=', 'done'),
                    ('product_version_hash', '=', product.version_hash),
                ], limit=1)
                if existing:
                    continue
                try:
                    with self.env.cr.savepoint():
                        raster = self.get_or_create(product, t)
                        results.append(
                            (product.id, raster.id, raster.state))
                except Exception as exc:
                    _logger.warning(
                        'meteo prerender failed: product=%s t=%s '
                        'err=%s', product.id, t, exc)
                    results.append((product.id, None, 'failed'))
                budget -= 1
        return results

    @api.model
    def cron_apply_retention(self):
        """Purge rasters older than product.retention_days."""
        product_model = self.env['meteo.product']
        products = product_model.search([('retention_days', '>', 0)])
        now = fields.Datetime.now()
        now_dt = fields.Datetime.from_string(now)
        purged = 0
        for product in products:
            cutoff = now_dt - timedelta(days=product.retention_days)
            cutoff_str = fields.Datetime.to_string(cutoff)
            old = self.search([
                ('product_id', '=', product.id),
                ('valid_from', '<', cutoff_str),
            ])
            if old:
                purged += len(old)
                # Attachments are unlinked by ondelete='set null' +
                # explicit unlink to free filestore space.
                attachments = old.mapped('cog_attachment_id')
                old.unlink()
                attachments.unlink()
        _logger.info('meteo.raster retention purged %s records', purged)
        return purged

    @api.model
    def cron_regen_stale(self, batch_size=20):
        """Regenerate rasters whose product version_hash drifted."""
        stale = self.search([
            ('state', '=', 'done'),
            ('is_stale', '=', True),
        ], limit=batch_size)
        for raster in stale:
            try:
                with self.env.cr.savepoint():
                    raster._compute_one()
            except Exception as exc:
                _logger.warning(
                    'meteo.raster regen failed for %s: %s',
                    raster.id, exc)
        return len(stale)

    # Core pipeline.
    @api.multi
    def _compute_one(self):
        self.ensure_one()
        product = self.product_id
        warnings = []
        t0 = time.time()
        try:
            target_dt = fields.Datetime.from_string(self.valid_from)
            stations = self.collect_stations(product, target_dt)
            n = len(stations)
            if n < max(int(product.min_stations or 0), 1):
                warnings.append('LOW_STATIONS')
                self.write({
                    'state': 'failed',
                    'method': 'none',
                    'n_stations_used': n,
                    'stations_json': json.dumps(stations),
                    'warnings_json': json.dumps(warnings),
                    'error_message': _(
                        'Only %s stations available, %s required.') % (
                            n, product.min_stations),
                })
                return
            grid_n = product.recommend_grid_size(n)
            method, params = product.recommend_method(n)
            # Warn when runtime conditions force a method or parameter
            # different from what the operator configured so that the
            # raster record documents the divergence.
            if method == 'idw_knn' and not product.idw_neighbors:
                warnings.append('METHOD_AUTO_SWITCHED_TO_KNN')
            if (method == 'idw' and n <= 3 and
                    abs(params.get('power', product.idw_power) -
                        product.idw_power) > 1e-6):
                warnings.append('IDW_POWER_OVERRIDDEN')
            stations, prep_meta = self._prepare_interpolation_inputs(
                product,
                stations,
                warnings,
            )
            n = len(stations)
            xs = np.array([s['x'] for s in stations], dtype=np.float64)
            ys = np.array([s['y'] for s in stations], dtype=np.float64)
            vs = np.array([s['value'] for s in stations],
                          dtype=np.float64)

            xmin, ymin = product.extent_xmin, product.extent_ymin
            xmax, ymax = product.extent_xmax, product.extent_ymax
            gx = np.linspace(xmin, xmax, grid_n)
            # North-up: first row is ymax, last row is ymin.
            gy = np.linspace(ymax, ymin, grid_n)
            grid = self._interpolate(method, params, xs, ys, vs, gx, gy)
            grid = np.clip(grid,
                           product.variable_id.min_value,
                           product.variable_id.max_value).astype(np.float32)
            # Quality warnings.
            if grid_n == product.grid_min:
                warnings.append('RESOLUTION_CAPPED_LOW')
            if grid_n == product.grid_max:
                warnings.append('RESOLUTION_CAPPED_HIGH')
            cog_bytes = self._write_cog(grid, xmin, ymin, xmax, ymax,
                                        product.srs)
            attachment = self._store_attachment(cog_bytes, target_dt)
            elapsed_ms = int((time.time() - t0) * 1000)
            if elapsed_ms > 2000:
                warnings.append('LONG_COMPUTE')
            params_to_store = dict(params)
            params_to_store['preprocess'] = prep_meta
            self.write({
                'state': 'done',
                'method': method,
                'n_stations_used': n,
                'grid_w': grid_n,
                'grid_h': grid_n,
                'compute_ms': elapsed_ms,
                'cog_attachment_id': attachment.id,
                'parameters_json': json.dumps(params_to_store),
                'stations_json': json.dumps(stations),
                'warnings_json': json.dumps(warnings),
                'product_version_hash': product.version_hash,
                'error_message': False,
            })
        except Exception as exc:
            _logger.exception('meteo.raster compute failed for %s', self)
            self.write({
                'state': 'failed',
                'error_message': '%s' % exc,
                'compute_ms': int((time.time() - t0) * 1000),
            })

    @api.model
    def _prepare_interpolation_inputs(self, product, stations, warnings):
        """Normalize station values before interpolation.

        This hook is the extension point for future DEM-aware
        corrections. Current implementation preserves existing behaviour
        (`none`) and records metadata for traceability.
        """
        mode = product.terrain_correction or 'none'
        metadata = {
            'mode': mode,
            'station_weighting': 'uniform',
        }
        # TODO[Phase 2]: support per-station quality weights
        # (sensor reliability / maintenance score / representativity)
        # and apply them in IDW as `w = w_distance * w_station`.
        if mode == 'none':
            return stations, metadata
        if mode == 'lapse_rate':
            warnings.append('TERRAIN_CORRECTION_NOT_IMPLEMENTED')
            metadata.update({
                'status': 'pending_dem_integration',
                'lapse_rate_c_per_km': product.lapse_rate_c_per_km,
            })
            return stations, metadata
        warnings.append('UNKNOWN_TERRAIN_CORRECTION')
        metadata['status'] = 'unknown_mode_fallback'
        return stations, metadata

    # Interpolation kernels.
    @api.model
    def _interpolate(self, method, params, xs, ys, vs, gx, gy):
        """Dispatch to the requested interpolation kernel."""
        if method == 'constant':
            return np.full((len(gy), len(gx)), vs[0], dtype=np.float64)
        if method == 'idw':
            return self._idw(xs, ys, vs, gx, gy,
                             power=params.get('power', 2.0))
        if method == 'idw_knn':
            return self._idw_knn(xs, ys, vs, gx, gy,
                                 power=params.get('power', 2.0),
                                 k=params.get('neighbors', 12))
        raise exceptions.UserError(_(
            'Unknown interpolation method: %s') % method)

    @api.model
    def _idw(self, xs, ys, vs, gx, gy, power=2.0, eps=1e-9):
        """Vectorized IDW using all stations.

        Loop is per station to keep memory bounded for large grids.
        """
        gxx, gyy = np.meshgrid(gx, gy)
        num = np.zeros(gxx.shape, dtype=np.float64)
        den = np.zeros(gxx.shape, dtype=np.float64)
        for i in range(len(xs)):
            d2 = (gxx - xs[i]) ** 2 + (gyy - ys[i]) ** 2
            w = 1.0 / (np.power(d2, power / 2.0) + eps)
            num += w * vs[i]
            den += w
        return num / den

    @api.model
    def _idw_knn(self, xs, ys, vs, gx, gy, power=2.0, k=12, eps=1e-9):
        """IDW restricted to the K nearest stations per cell.
        Uses scipy.spatial.cKDTree when available, falls back to plain
        IDW otherwise.
        TODO[Phase 2]: replace fallback with a chunked numpy approach
        instead of degrading silently.
        """
        if cKDTree is None:
            _logger.warning(
                'scipy not available, falling back to full IDW.')
            return self._idw(xs, ys, vs, gx, gy, power=power, eps=eps)
        k = max(1, min(int(k), len(xs)))
        tree = cKDTree(np.column_stack([xs, ys]))
        gxx, gyy = np.meshgrid(gx, gy)
        pts = np.column_stack([gxx.ravel(), gyy.ravel()])
        d, idx = tree.query(pts, k=k)
        if k == 1:
            d = d[:, None]
            idx = idx[:, None]
        w = 1.0 / (np.power(d, power) + eps)
        out = np.sum(w * vs[idx], axis=1) / np.sum(w, axis=1)
        return out.reshape(gxx.shape)

    # COG writer (Pillow + gdal_translate subprocess).
    @api.model
    def _write_cog(self, arr, xmin, ymin, xmax, ymax, srs):
        """Write the float32 grid as a Cloud-Optimized GeoTIFF.

        Strategy: Pillow writes a plain Float32 TIFF (no georef), then
        gdal_translate transforms it to a properly tiled COG with
        georeferencing applied via -a_srs / -a_ullr.

        TODO[Phase 2]: switch to rasterio for direct COG writing once
        the dependency is approved, or call gdal_translate via a
        persistent Python 3 sidecar to avoid subprocess overhead.
        """
        tmpdir = tempfile.mkdtemp(prefix='meteo_cog_')
        plain_path = os.path.join(tmpdir, 'plain.tif')
        cog_path = os.path.join(tmpdir, 'out.cog.tif')
        try:
            Image.fromarray(arr, mode='F').save(plain_path, format='TIFF')
            cmd = [
                'gdal_translate', '-q',
                '-a_srs', srs,
                '-a_ullr', str(xmin), str(ymax), str(xmax), str(ymin),
                '-of', 'COG',
                '-co', 'COMPRESS=DEFLATE',
                '-co', 'PREDICTOR=3',
                '-co', 'BLOCKSIZE=256',
                '-co', 'OVERVIEWS=AUTO',
                plain_path, cog_path,
            ]
            subprocess.check_call(cmd)
            with open(cog_path, 'rb') as fh:
                return fh.read()
        finally:
            for p in (plain_path, cog_path):
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass
            try:
                os.rmdir(tmpdir)
            except OSError:
                pass

    @api.multi
    def _store_attachment(self, cog_bytes, target_dt):
        self.ensure_one()
        attach_model = self.env['ir.attachment']
        ts_str = fields.Datetime.to_string(target_dt) \
            if isinstance(target_dt, datetime) else target_dt
        safe_ts = ts_str.replace(':', '').replace(' ', 'T')
        fname = 'meteo_%s_%s_%s.tif' % (
            self.product_id.id, self.id, safe_ts)
        # Replace previous attachment, if any (regen flow).
        if self.cog_attachment_id:
            self.cog_attachment_id.unlink()
        attachment = attach_model.create({
            'name': fname,
            'datas_fname': fname,
            'datas': base64.b64encode(cog_bytes),
            'res_model': 'meteo.raster',
            'res_id': self.id,
            'mimetype': 'image/tiff',
        })
        return attachment
