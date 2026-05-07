# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import hashlib
import json
import logging
import math
from datetime import timedelta

from odoo import api, exceptions, fields, models, _


_logger = logging.getLogger(__name__)


class MeteoProduct(models.Model):
    _name = 'meteo.product'
    _description = 'Meteorological Product'
    _order = 'name'

    name = fields.Char(
        string='Name',
        required=True,
        translate=True,
    )

    variable_id = fields.Many2one(
        comodel_name='meteo.variable',
        string='Variable',
        required=True,
        ondelete='restrict',
    )

    active = fields.Boolean(
        default=True,
    )

    description = fields.Text(
        string='Description',
        translate=True,
    )

    timezone = fields.Char(
        string='Timezone',
        default='Europe/Madrid',
        required=True,
        help='IANA timezone used for daily aggregations (e.g. '
             'Europe/Madrid, Europe/London). Readings are bucketed '
             'in local time so that "daily" means midnight-to-midnight '
             'in the community timezone, not UTC.',
    )

    # Geographic extent (EPSG:3857 Web Mercator, meters).
    # TODO[Phase 2]: support shared meteo.extent records and snap-to-tile.
    srs = fields.Char(
        string='SRS',
        default='EPSG:3857',
        required=True,
        help='Spatial Reference System the raster is generated in. '
             'Default EPSG:3857 (Web Mercator) is what Leaflet consumes '
             'natively, avoiding client-side reprojection.',
    )

    extent_xmin = fields.Float(
        string='X min',
        digits=(16, 3),
    )

    extent_ymin = fields.Float(
        string='Y min',
        digits=(16, 3),
    )

    extent_xmax = fields.Float(
        string='X max',
        digits=(16, 3),
    )

    extent_ymax = fields.Float(
        string='Y max',
        digits=(16, 3),
    )

    # Resolution heuristics.
    auto_resolution = fields.Boolean(
        string='Automatic Resolution',
        default=True,
        help='When enabled, grid size is derived from the average distance '
             'between contributing stations (Nyquist-like rule). When '
             'disabled, "Grid Size" is used.',
    )

    grid_size = fields.Integer(
        string='Grid Size (px)',
        default=512,
        help='Manual grid side in pixels (square raster). Ignored when '
             'Automatic Resolution is on.',
    )

    grid_min = fields.Integer(
        string='Grid Min (px)',
        default=256,
        help='Lower bound for the auto-resolution heuristic.',
    )

    grid_max = fields.Integer(
        string='Grid Max (px)',
        default=2048,
        help='Upper bound for the auto-resolution heuristic.',
    )

    # Interpolation parameters.
    idw_power = fields.Float(
        string='IDW Power',
        default=2.0,
        help='Power exponent of the Inverse Distance Weighting '
             'interpolator.',
    )

    idw_neighbors = fields.Integer(
        string='IDW Neighbors (k)',
        default=0,
        help='If > 0, only the K nearest stations are used (KDTree). '
             '0 = use all stations. Recommended for n_stations > 30.',
    )

    terrain_correction = fields.Selection(
        selection=[
            ('none', 'None'),
            ('lapse_rate', 'Lapse-rate (DEM-ready)'),
        ],
        string='Terrain Correction',
        default='none',
        help='Pre-interpolation correction strategy. "None" keeps '
             'station values untouched. "Lapse-rate" reserves the '
             'pipeline hook for DEM-driven temperature adjustments.',
    )

    lapse_rate_c_per_km = fields.Float(
        string='Lapse Rate (C/km)',
        default=-6.5,
        help='Environmental lapse rate used by the terrain-correction '
             'hook when DEM adjustments are enabled.',
    )

    # Data quality controls.
    min_stations = fields.Integer(
        string='Min Stations',
        default=1,
        help='Minimum number of stations with valid data needed to '
             'generate a raster. Below this, generation is aborted.',
    )

    aggregation = fields.Selection(
        selection='_get_aggregation_selection',
        string='Aggregation',
        default='avg',
        required=True,
    )

    @api.model
    def _get_aggregation_selection(self):
        """Return the list of valid aggregation codes.

        Override in an inherited module to add extra aggregation types
        (e.g. ET0 Penman-Monteith). The corresponding SQL operator or
        method must also be registered in meteo_raster._AGG_SQL or
        handled as a special case in collect_stations_for_product.
        """
        aggregation_model = self.env['meteo.aggregation']
        catalog = aggregation_model.search([
            ('active', '=', True),
        ], order='sequence, name, id')
        if catalog:
            return [(item.code, item.name) for item in catalog]
        return [
            ('avg', 'Average'),
            ('sum', 'Sum'),
            ('min', 'Min'),
            ('max', 'Max'),
            ('last', 'Last value'),
        ]

    # Devices to exclude from this product even if their sensor type
    # matches the variable. Used to mask broken or test stations.
    excluded_device_ids = fields.Many2many(
        comodel_name='mdm.measurement.device',
        relation='meteo_product_excluded_device_rel',
        column1='product_id',
        column2='device_id',
        string='Excluded Devices',
        help='Devices listed here are ignored when collecting readings '
             'for this product, even if their sensors match the '
             'variable type.',
    )

    # Frontend slider + pre-render configuration. The slider in the
    # viewer reuses these values: it offers a step matching the
    # pre-rendered cadence and a range covering the history window so
    # the user only sees timestamps for which a raster exists (or will
    # exist after the next cron run). The same `step_minutes` is used
    # as the aggregation window: every raster aggregates readings
    # falling in the half-step before and after its timestamp, so the
    # whole timeline is covered without overlap nor gaps.
    history_minutes = fields.Integer(
        string='History (min)',
        default=1440,
        help='How far back in time rasters are generated and offered '
             'in the time slider. Default 1440 = 24 h. Use 10080 for '
             '7 days, 525600 for 1 year.',
    )

    step_minutes = fields.Integer(
        string='Step (min)',
        default=60,
        help='Distance in minutes between two consecutive rasters '
             '(and the granularity of the time slider). Each raster '
             'aggregates the readings of the half-step centered on '
             'its timestamp. Use 1440 for daily.',
    )

    # Pre-render scheduling.
    is_prerendered = fields.Boolean(
        string='Pre-render',
        default=False,
        help='When enabled, the cron generates rasters for every step '
             'in [now - History, now] that is missing or outdated.',
    )

    retention_days = fields.Integer(
        string='Retention (days)',
        default=30,
        help='Older rasters are purged by the retention cron. '
             '0 = keep forever.',
    )

    # Determinism. Any change to a structural field bumps version_hash;
    # rasters tagged with a stale hash are considered outdated and the
    # cron will regenerate them.
    version_hash = fields.Char(
        string='Version Hash',
        compute='_compute_version_hash',
        store=True,
        readonly=True,
        help='SHA-1 (truncated) of the structural fields of this '
             'product. Bumped on any change that affects raster output.',
    )

    raster_ids = fields.One2many(
        comodel_name='meteo.raster',
        inverse_name='product_id',
        string='Generated Rasters',
    )

    raster_count = fields.Integer(
        string='Rasters',
        compute='_compute_raster_count',
    )

    @api.depends('raster_ids')
    def _compute_raster_count(self):
        for record in self:
            record.raster_count = len(record.raster_ids)

    @api.depends('variable_id', 'srs',
                 'extent_xmin', 'extent_ymin',
                 'extent_xmax', 'extent_ymax',
                 'auto_resolution', 'grid_size',
                 'grid_min', 'grid_max',
                 'idw_power', 'idw_neighbors',
                 'terrain_correction', 'lapse_rate_c_per_km',
                 'min_stations', 'step_minutes',
                 'aggregation',
                 'aggregation', 'timezone',
                 'excluded_device_ids')
    def _compute_version_hash(self):
        for record in self:
            payload = json.dumps([
                record.variable_id.id,
                record.srs,
                record.extent_xmin, record.extent_ymin,
                record.extent_xmax, record.extent_ymax,
                record.auto_resolution, record.grid_size,
                record.grid_min, record.grid_max,
                record.idw_power, record.idw_neighbors,
                record.terrain_correction,
                record.lapse_rate_c_per_km,
                record.min_stations, record.step_minutes,
                record.aggregation,
                record.timezone,
                sorted(record.excluded_device_ids.ids),
            ], sort_keys=True)
            record.version_hash = hashlib.sha1(
                payload.encode('utf-8')).hexdigest()[:12]

    @api.constrains('extent_xmin', 'extent_ymin',
                    'extent_xmax', 'extent_ymax')
    def _check_extent(self):
        for record in self:
            empty = (record.extent_xmin == 0.0 and
                     record.extent_ymin == 0.0 and
                     record.extent_xmax == 0.0 and
                     record.extent_ymax == 0.0)
            if empty:
                continue
            if record.extent_xmax <= record.extent_xmin or \
                    record.extent_ymax <= record.extent_ymin:
                raise exceptions.ValidationError(_(
                    'Invalid extent: max coordinates must be greater '
                    'than min coordinates.'))

    @api.constrains('grid_min', 'grid_max', 'grid_size')
    def _check_grid_bounds(self):
        for record in self:
            if record.grid_min < 16 or record.grid_max < record.grid_min:
                raise exceptions.ValidationError(_(
                    'Invalid grid bounds: grid_min must be >= 16 and '
                    'grid_max >= grid_min.'))
            if not record.auto_resolution and record.grid_size < 16:
                raise exceptions.ValidationError(_(
                    'Manual grid size must be at least 16 px.'))

    @api.constrains('step_minutes', 'history_minutes',
                    'retention_days', 'min_stations')
    def _check_temporal_and_quality_values(self):
        for record in self:
            if int(record.step_minutes or 0) <= 0:
                raise exceptions.ValidationError(_(
                    'Step (min) must be greater than zero.'))
            if int(record.history_minutes or 0) <= 0:
                raise exceptions.ValidationError(_(
                    'History (min) must be greater than zero.'))
            if int(record.retention_days or 0) < 0:
                raise exceptions.ValidationError(_(
                    'Retention (days) cannot be negative.'))
            if int(record.min_stations or 0) < 1:
                raise exceptions.ValidationError(_(
                    'Min Stations must be at least 1.'))

    @api.constrains('variable_id', 'aggregation')
    def _check_variable_aggregation_compatibility(self):
        for record in self:
            variable = record.variable_id
            if not variable or not record.aggregation:
                continue
            allowed_codes = set(
                variable.compatible_aggregation_ids.mapped('code'))
            if not allowed_codes:
                continue
            if record.aggregation not in allowed_codes:
                raise exceptions.ValidationError(_(
                    'Aggregation "%s" is not compatible with variable '
                    '"%s".') % (record.aggregation, variable.name))

    @api.multi
    def recommend_grid_size(self, n_stations):
        """Return the recommended grid side (px) for a given station count.

        Heuristic: the cell size should not be smaller than half the
        average inter-station distance over the extent (Nyquist-like).
        Anything finer is just IDW noise.
        """
        self.ensure_one()
        if not self.auto_resolution:
            return max(16, self.grid_size)
        if n_stations <= 1:
            # 1 station -> constant raster, smallest grid is enough.
            return self.grid_min
        side = max(self.extent_xmax - self.extent_xmin,
                   self.extent_ymax - self.extent_ymin)
        area = (self.extent_xmax - self.extent_xmin) * \
               (self.extent_ymax - self.extent_ymin)
        d_mean = math.sqrt(max(area, 1.0) / float(n_stations))
        cell_target = d_mean / 2.0
        n_cells = int(round(side / max(cell_target, 1.0)))
        n_cells = max(self.grid_min, min(self.grid_max, n_cells))
        return n_cells

    @api.multi
    def recommend_method(self, n_stations):
        """Return ('method', extra_params) recommended for n stations."""
        self.ensure_one()
        if n_stations <= 0:
            return ('none', {})
        if n_stations == 1:
            return ('constant', {})
        if n_stations <= 3:
            return ('idw', {'power': 1.0, 'neighbors': 0})
        if n_stations > 30 and self.idw_neighbors == 0:
            # Auto-pick KNN to keep compute time bounded.
            return ('idw_knn', {
                'power': self.idw_power,
                'neighbors': 12,
            })
        if self.idw_neighbors > 0:
            return ('idw_knn', {
                'power': self.idw_power,
                'neighbors': self.idw_neighbors,
            })
        return ('idw', {
            'power': self.idw_power,
            'neighbors': 0,
        })

    @api.multi
    def action_analyze_data(self):
        """Compute a dry-run report (no raster written) and store it on
        a transient wizard for the user to inspect.

        TODO[Phase 2]: render results in a dedicated wizard view.
        """
        self.ensure_one()
        now = fields.Datetime.from_string(fields.Datetime.now())
        stations = self.env['meteo.raster'].collect_stations(self, now)
        n = len(stations)
        grid = self.recommend_grid_size(n)
        method, params = self.recommend_method(n)
        # Lightweight notification using a wizard-like dict view.
        message = _(
            'Stations available: %s\n'
            'Recommended grid: %s x %s\n'
            'Recommended method: %s\n'
            'Params: %s',
        ) % (n, grid, grid, method, json.dumps(params))
        raise exceptions.UserError(message)

    @api.multi
    def action_recompute_extent(self):
        """Compute the bounding box of all sensor devices that match the
        product's variable (excluding manually excluded ones) and write
        it to extent_xmin/ymin/xmax/ymax in the product SRS.

        Adds a 5 % padding on each side so stations near the border are
        not painted right against the raster edge.
        """
        self.ensure_one()
        if not self.variable_id:
            raise exceptions.UserError(_(
                'Set a variable before recomputing the extent.'))
        try:
            srs_epsg = int((self.srs or 'EPSG:3857').split(':')[-1])
        except (ValueError, AttributeError):
            raise exceptions.UserError(_(
                'Unsupported SRS %s. Use EPSG:NNNN.') % self.srs)
        sensor_type_ids = tuple(
            self.variable_id.sensor_type_ids.ids) or (0,)
        excluded_device_ids = tuple(self.excluded_device_ids.ids) or (0,)
        cr = self.env.cr
        cr.execute(
            """
            SELECT MIN(ST_X(ST_Transform(g.geom, %s))),
                   MIN(ST_Y(ST_Transform(g.geom, %s))),
                   MAX(ST_X(ST_Transform(g.geom, %s))),
                   MAX(ST_Y(ST_Transform(g.geom, %s)))
            FROM mdm_gis_measurement_device g
            JOIN mdm_measurement_device d ON d.name = g.name
            JOIN mdm_measurement_device_sensor s ON s.device_id = d.id
            WHERE s.type_id IN %s
              AND g.geom IS NOT NULL
              AND d.id NOT IN %s
            """,
            (srs_epsg, srs_epsg, srs_epsg, srs_epsg,
             sensor_type_ids, excluded_device_ids))
        row = cr.fetchone()
        if not row or row[0] is None:
            raise exceptions.UserError(_(
                'No georeferenced devices found for variable %s.',
            ) % self.variable_id.name)
        xmin, ymin, xmax, ymax = row
        dx = xmax - xmin
        dy = ymax - ymin
        # Degenerate bbox (single point or near-zero span): fall back to
        # the bbox of ALL georeferenced devices in the database, so the
        # raster covers the whole WUA area instead of a tiny region
        # around the single sensor. If even that is degenerate, pad by
        # 5 km / ~0.05 deg as a last resort.
        min_half_span = 5000.0 if srs_epsg == 3857 else 0.05
        if dx < 2 * min_half_span or dy < 2 * min_half_span:
            cr.execute(
                """
                SELECT MIN(ST_X(ST_Transform(geom, %s))),
                       MIN(ST_Y(ST_Transform(geom, %s))),
                       MAX(ST_X(ST_Transform(geom, %s))),
                       MAX(ST_Y(ST_Transform(geom, %s)))
                FROM mdm_gis_measurement_device
                WHERE geom IS NOT NULL
                """,
                (srs_epsg, srs_epsg, srs_epsg, srs_epsg))
            fallback = cr.fetchone()
            if fallback and fallback[0] is not None:
                fxmin, fymin, fxmax, fymax = fallback
                # Use the fallback bbox if it is wider than the
                # variable-restricted one.
                if fxmax - fxmin > dx:
                    xmin, xmax = fxmin, fxmax
                    dx = xmax - xmin
                if fymax - fymin > dy:
                    ymin, ymax = fymin, fymax
                    dy = ymax - ymin
        # Final guard against still-degenerate bboxes.
        if dx < 2 * min_half_span:
            cx = (xmin + xmax) / 2.0
            xmin = cx - min_half_span
            xmax = cx + min_half_span
            dx = xmax - xmin
        if dy < 2 * min_half_span:
            cy = (ymin + ymax) / 2.0
            ymin = cy - min_half_span
            ymax = cy + min_half_span
            dy = ymax - ymin
        pad_x = 0.05 * dx
        pad_y = 0.05 * dy
        self.write({
            'extent_xmin': xmin - pad_x,
            'extent_ymin': ymin - pad_y,
            'extent_xmax': xmax + pad_x,
            'extent_ymax': ymax + pad_y,
        })
        return True

    @api.multi
    def action_recompute_rasters(self):
        """Generate (or refresh) one raster at "now" for each selected
        product.

        Useful when the rasters have been wiped or the product config
        changed and the user wants an immediate visual check without
        waiting for the cron. Errors on one product do not abort the
        others (savepoint pattern).
        """
        raster_model = self.env['meteo.raster']
        now = fields.Datetime.from_string(fields.Datetime.now())
        failures = []
        for product in self:
            try:
                with self.env.cr.savepoint():
                    raster_model.get_or_create(product, now)
            except Exception as e:
                _logger.warning(
                    'Failed to recompute raster for %s: %s',
                    product.name, e)
                failures.append((product.name, str(e)))
        if failures:
            raise exceptions.UserError(_(
                'Recompute finished with errors:\n%s',
            ) % '\n'.join('- %s: %s' % f for f in failures))
        return True

    @api.multi
    def action_backfill_rasters(self, max_steps=10000, commit_every=20):
        """Generate every missing raster in the pre-render window.

        For each selected product, walk the timeline from `now` back to
        `now - history_minutes` in steps of `step_minutes` and call
        `meteo.raster.get_or_create` for every timestep. The
        `get_or_create` call short-circuits when a fresh raster already
        exists, so reruns are cheap and resumable.

        Errors on a single timestep do not abort the rest (savepoint
        pattern). The transaction is committed every `commit_every`
        new rasters so a long backfill is durable even if interrupted.

        `max_steps` is a safety cap to avoid runaway loops if the user
        sets back=1y / step=1min by mistake.
        """
        raster_model = self.env['meteo.raster']
        now = fields.Datetime.from_string(fields.Datetime.now())
        total_done = 0
        total_skipped = 0
        total_failed = 0
        since_commit = 0
        for product in self:
            step = max(int(product.step_minutes or 0), 1)
            back = max(int(product.history_minutes or 0), step)
            n_steps = min(back // step, max_steps)
            anchor_minute = (now.minute // step) * step \
                if step < 60 else 0
            anchor = now.replace(minute=anchor_minute,
                                 second=0, microsecond=0)
            for i in range(n_steps + 1):
                t = anchor - timedelta(minutes=step * i)
                t_str = fields.Datetime.to_string(t)
                # Cheap pre-check: if a fresh raster exists, skip
                # without entering get_or_create (no savepoint cost).
                existing = raster_model.search([
                    ('product_id', '=', product.id),
                    ('valid_from', '<=', t_str),
                    ('valid_to', '>=', t_str),
                    ('state', '=', 'done'),
                    ('product_version_hash', '=', product.version_hash),
                ], limit=1)
                if existing:
                    total_skipped += 1
                    continue
                try:
                    with self.env.cr.savepoint():
                        raster_model.get_or_create(product, t)
                    total_done += 1
                    since_commit += 1
                    if since_commit >= commit_every:
                        self.env.cr.commit()
                        since_commit = 0
                        _logger.info(
                            'meteo backfill: committed %s rasters '
                            '(product=%s)', total_done, product.id)
                except Exception as exc:
                    _logger.warning(
                        'meteo backfill failed: product=%s t=%s err=%s',
                        product.id, t, exc)
                    total_failed += 1
        if since_commit:
            self.env.cr.commit()
        raise exceptions.UserError(_(
            'Backfill finished. Computed: %s, already up-to-date: %s, '
            'failed: %s.',
        ) % (total_done, total_skipped, total_failed))
