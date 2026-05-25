.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

==========
Base Meteo
==========

Meteorological raster generation engine for Odoo 10.

This module reads sensor readings from the MDM (Measurement Device Management)
layer, interpolates them spatially, and produces Cloud-Optimised GeoTIFF (COG)
raster files that the movallibs GIS viewer consumes to render animated
meteorological maps.

Key Features
============

* **Variable catalogue**: configurable meteorological variables (T, P, HR…)
  with physical range validation, colour ramps and compatible aggregation
  methods per variable.
* **Aggregation catalogue**: named temporal aggregation methods (avg, sum, min,
  max, last) linked to variables via Many2many; extensible without code changes.
* **Product configuration**: each ``meteo.product`` combines a variable, a
  spatial extent, a temporal cadence, an interpolation strategy and quality
  thresholds into one deployable product.
* **IDW interpolation**: Inverse Distance Weighting with configurable power
  parameter; k-NN variant (via ``scipy.cKDTree``) for large networks.
* **Automatic method selection**: switches from IDW to k-NN or constant
  depending on the number of available stations; records warnings when runtime
  conditions diverge from the operator configuration.
* **Timezone-aware daily aggregation**: for step ≥ 1440 min the aggregation
  window is aligned to local midnight in the product's IANA timezone
  (``pytz``), not UTC.
* **Cloud-Optimised GeoTIFF output**: rasters are written as COG attachments
  via GDAL (``gdal_translate`` + ``gdaladdo``); stored in the Odoo filestore.
* **Station snapshot**: each raster stores a JSON list of the stations and
  values used for the interpolation, enabling the viewer to render exact
  input markers with no recomputation.
* **Staleness detection**: ``is_stale`` flag (computed + searchable) detects
  rasters whose product configuration changed after generation.
* **Pre-render cron**: ``cron_prerender`` fills the timeline window
  (``history_minutes``) backwards from now, bounded by a ``batch_size``
  budget to keep transactions short.
* **Retention cron**: ``cron_apply_retention`` purges rasters older than
  ``product.retention_days``, including filestore attachments.
* **Stale-regen cron**: ``cron_regen_stale`` picks up rasters whose
  ``version_hash`` drifted and regenerates them up to a batch limit.
* **Version hash**: SHA-1 digest of the product's interpolation parameters;
  any configuration change invalidates pre-rendered rasters automatically.
* **Backfill action**: ``action_backfill_rasters`` walks the full history
  window and regenerates missing rasters; commits in chunks to avoid
  long-transaction timeouts.
* **Analyse action**: ``action_analyze_data`` shows a live count of stations,
  the recommended grid size and interpolation method for the current moment.
* **Auto-extent action**: ``action_recompute_extent`` derives the bounding box
  from the stations visible to the product.
* **Generic seed products**: T / P / HR hourly and daily template products
  shipped with ``noupdate="1"``; operators activate and configure the extent
  per deployment.
* **Security**: two-tier permission system (``group_meteo_user`` read-only,
  ``group_meteo_manager`` full CRUD).

Technical Overview
==================

Models
------

``meteo.variable``
    Catalogue of meteorological variables: code, physical min/max, colour
    ramp (JSON), default IDW power, compatible aggregations (Many2many to
    ``meteo.aggregation``).

``meteo.aggregation``
    Catalogue of temporal aggregation methods: code (``avg``, ``sum``,
    ``min``, ``max``, ``last``), display name, sequence, computed Python
    method name suffix. SQL-unique constraint on ``code``.

``meteo.product``
    One deployable product per variable / cadence / area combination.
    Holds spatial extent (EPSG:3857 by default), temporal parameters
    (``step_minutes``, ``history_minutes``, ``retention_days``), IDW
    parameters, quality thresholds and terrain-correction hooks.
    ``version_hash`` (SHA-1) invalidates pre-rendered rasters on any
    parameter change.

``meteo.raster``
    One record per (product, valid_from) pair. Stores state
    (``draft`` / ``done`` / ``failed``), method used, station count, COG
    attachment, station snapshot JSON, warnings JSON, error message and
    the ``product_version_hash`` at generation time.

HTTP Endpoints
--------------

All endpoints require ``auth='user'``.

``POST /meteo/init_config``
    Returns product metadata (extent, step, SRS, colour ramp, units,
    version_hash) needed to initialise the viewer.

``GET  /meteo/get_raster``
    Streams the COG bytes for a given ``product_id`` and timestamp ``t``.
    On cache-miss triggers on-demand generation via ``get_or_create``.

``POST /meteo/get_raster_urls``
    Batch endpoint: returns a list of ``{ts, url, raster_id,
    version_hash, state, warnings}`` descriptors for a time range
    (``from_t`` … ``to_t``). Used by the viewer prefetch logic to
    resolve a full slider window in one round-trip.

``POST /meteo/stations``
    Returns the station markers (lon, lat, value, measurement_time,
    name) for a given product and timestamp. Uses the stored
    ``stations_json`` snapshot when available; falls back to a live SQL
    query.

``POST /meteo/explain_point``
    For a clicked map coordinate (x, y in product SRS), returns the
    IDW contribution weights and individual station values that produced
    the interpolated result at that point.

Interpolation Pipeline (``_compute_one``)
-----------------------------------------

1. Collect contributing station readings via ``MeteoRaster.collect_stations``
   (SQL with PostGIS spatial filter, temporal window, aggregation).
2. Validate station count against ``min_stations``; abort with ``failed``
   state if below threshold.
3. Determine grid size (auto Nyquist heuristic or manual ``grid_size``).
4. Select interpolation method (``constant`` → ``idw`` → ``idw_knn``)
   based on station count and product settings; record AUTO_SWITCHED
   warnings on divergence.
5. Apply terrain correction hook (currently ``lapse_rate`` placeholder).
6. Build NumPy coordinate arrays and call the IDW kernel (plain or k-NN).
7. Write the float32 NumPy array to a GeoTIFF in memory using PIL/GDAL,
   then convert to COG with ``gdal_translate -of COG`` and add overviews
   with ``gdaladdo``.
8. Store the COG as an ``ir.attachment``, write metadata fields and
   serialise the station snapshot to ``stations_json``.

Dependencies
============

Python packages (declared in ``external_dependencies``):

* ``Pillow`` (PIL) — GeoTIFF pixel writing
* ``numpy`` — raster array operations
* ``scipy`` (optional) — ``cKDTree`` for k-NN IDW; graceful fallback to
  plain IDW when absent
* ``pytz`` (optional) — timezone-aware daily aggregation windows;
  graceful fallback to UTC when absent

System binaries:

* ``gdal_translate`` — COG conversion
* ``gdaladdo`` — overview pyramid generation

Odoo module dependencies:

* ``mdm_sensor_management`` — measurement device and sensor models
* ``mdm_sensor_management_gis`` — GIS geometry on measurement devices

Installation
============

1. Ensure GDAL command-line tools are installed on the server::

       apt install gdal-bin

2. Install Python dependencies into the virtualenv::

       pip install Pillow numpy scipy pytz

3. Add ``base_meteo`` to the ``addons_path`` in ``odoorc_v10`` and
   install via the backend or::

       venv2.7/bin/python2.7 ocb/odoo-bin -c odoorc_v10 \
           -d <dbname> -i base_meteo --stop-after-init

Configuration
=============

After installing:

1. Assign permissions via *Settings → Users*: ``Meteo User`` (read-only)
   or ``Meteo Manager`` (full CRUD).
2. Go to *Meteo → Configuration → Variables* and verify the variable
   catalogue (T, P, HR are pre-loaded).
3. Go to *Meteo → Configuration → Aggregations* to review the aggregation
   methods.
4. Go to *Meteo → Configuration → Products* and activate one of the
   template products (they ship with ``active = False``):

   a. Set the spatial **extent** (X min / Y min / X max / Y max) in
      EPSG:3857 (Web Mercator) metres. Use *Recompute Extent* to derive
      it automatically from visible stations.
   b. Review ``step_minutes``, ``history_minutes``, ``min_stations``.
   c. Enable *Pre-render* to let the cron fill the raster timeline.

5. The three cron jobs are installed but **inactive** by default. Enable
   them from *Settings → Technical → Automation → Scheduled Actions*:

   * **Meteo: Pre-render scheduled rasters** (recommended: every 15–30 min)
   * **Meteo: Regenerate stale rasters** (recommended: every 60 min)
   * **Meteo: Apply raster retention** (recommended: daily)

Usage
=====

Generating a raster on demand
------------------------------

From *Meteo → Rasters*, create a record linked to a product and a
``valid_from`` timestamp, then click *Compute*. Alternatively, call the
``/meteo/get_raster`` endpoint with a ``t`` parameter — it triggers
``get_or_create`` automatically.

Backfilling historical rasters
--------------------------------

From the product form, click *Backfill Rasters*. This walks the full
``history_minutes`` window backwards and generates any missing records,
committing every 20 rasters to avoid long-transaction timeouts.

Diagnosing a product
--------------------

Click *Analyse Data* on the product form to see, for the current moment:

* How many stations have valid readings inside the aggregation window.
* The recommended grid size (Nyquist heuristic).
* Which interpolation method would be selected and why.

Viewer integration (movallibs)
-------------------------------

``WorkModeMeteo`` in ``movallibs`` communicates with this module through
the HTTP API:

1. ``/meteo/init_config`` — on viewer load.
2. ``/meteo/get_raster_urls`` — one batch call per slider scrub to
   resolve the prefetch window (5 steps forward / 1 back).
3. ``/meteo/get_raster`` — fetches missing COG bytes and caches them in
   IndexedDB (Dexie, up to 1 GB with LRU eviction).
4. ``/meteo/stations`` — on frame change to render station markers.
5. ``/meteo/explain_point`` — on map click to show IDW contributions.

Roadmap
=======

The following items are planned but not yet implemented:

Short term
----------

* **Translations** — export ``es.po`` and ``ca_ES.po`` for all user-facing
  strings in the module (currently no ``.po`` files exist).
* **Web Worker for GeoTIFF decode** — move GeoTIFF parsing out of the
  main browser thread in ``meteo_mode`` to avoid UI jank on large rasters.
* **Service Worker HTTP cache** — complement the Dexie IndexedDB cache with
  a Service Worker layer to survive page reloads without re-fetching COGs.

Medium term
-----------

* **``meteo.extent`` model** — shared, named geographic extents that multiple
  products can reference; snap-to-tile alignment helpers.
* **Background model integration (ERA5 / AgERA5)** — optional
  ``background_product_id`` on ``meteo.product``; the interpolation operates
  on the station residual (additive for T/HR, multiplicative for P) relative
  to the background raster, then sums the interpolated residual back onto the
  background field. This significantly improves accuracy with sparse networks.
* **Terrain correction (DEM lapse-rate)** — complete the lapse-rate hook:
  load a DEM attachment, compute station elevations via PostGIS
  ``ST_Value``, reduce readings to sea level before interpolation, then
  restore the elevation gradient on the output raster.
* **``queue_job`` integration** — offload ``_compute_one`` to background
  workers via the OCA ``queue_job`` module to avoid blocking web-worker
  processes during heavy raster generation.

Long term
---------

* **``meteo.product.snapshot`` model** — periodic snapshots of product
  statistics (station count, method, coverage) for auditing and dashboards.
* **Scheduled cron** ``meteo_check_mask`` — detect products whose
  station coverage drops below ``min_stations`` and send alert notifications
  to managers.
* **Kriging / co-Kriging interpolation** — variogram-based geostatistical
  method as an alternative to IDW for products with well-characterised
  spatial correlation structure.
* **Multi-product viewer mode** — composite view combining two products
  (e.g. T and P simultaneously) with independent colour ramps and sliders.

Known Limitations
=================

* The GDAL COG conversion requires ``gdal_translate`` and ``gdaladdo``
  installed as system binaries. Pure-Python alternatives are not yet
  supported.
* ``scipy`` is optional: without it, k-NN IDW falls back to plain IDW
  (all stations), which may be slow for networks with > 100 stations.
* ``pytz`` is optional: without it, daily aggregation windows are computed
  in UTC regardless of the ``timezone`` field.
* The ``lapse_rate`` terrain correction is a pipeline hook only; the DEM
  loading and elevation query are not yet implemented.
* Raster generation is synchronous (no queue); for products with very
  large grids or many stations it may block the Odoo worker process for
  several seconds.

Credits
=======

* Moval Agroingeniería S.L.

Contributors
------------

* Alberto Hernández <ahernandez@moval.es>
* Eduardo Iniesta <einiesta@moval.es>
* Miguel Mora <mmora@moval.es>
* Juanu Sandoval <jsandoval@moval.es>
* Salvador Sánchez <ssanchez@moval.es>
* Jorge Vera <jvera@moval.es>

Maintainer
----------

.. image:: https://raw.githubusercontent.com/MovalAgroingenieria/public-assets/master/logos/logo_moval_small.png
   :target: http://moval.es
   :alt: Moval Agroingeniería

This module is maintained by Moval Agroingeniería.

