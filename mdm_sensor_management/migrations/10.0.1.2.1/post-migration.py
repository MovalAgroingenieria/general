# -*- coding: utf-8 -*-
# Copyright 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging


_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    _logger.info('mdm_sensor_management post-migration 10.0.1.2.1 started')

    # 1. Remove duplicate readings with the same (sensor_id, measurement_time),
    #    keeping the newest row (MAX(id)).
    cr.execute("""
        DELETE FROM mdm_measurement_device_sensor_reading r
        USING (
            SELECT sensor_id, measurement_time, MAX(id) AS keep_id
            FROM mdm_measurement_device_sensor_reading
            WHERE measurement_time >= '2026-10-22 00:00:00'
            GROUP BY sensor_id, measurement_time
            HAVING COUNT(*) > 1
        ) dup
        WHERE r.sensor_id = dup.sensor_id
          AND r.measurement_time = dup.measurement_time
          AND r.id <> dup.keep_id
    """)
    _logger.info(
        'Removed %d duplicate sensor readings since 2026-10-22.',
        cr.rowcount,
    )

    # 2. Temporarily rename out-of-sync reading names to avoid unique(name)
    #    collisions while normalizing timestamps back to UTC.
    cr.execute("""
        UPDATE mdm_measurement_device_sensor_reading r
        SET name = '__tmp_reading_name__' || r.id::text
        FROM mdm_measurement_device_sensor s
        JOIN mdm_measurement_device d ON d.id = s.device_id
        WHERE r.sensor_id = s.id
          AND r.measurement_time >= '2026-10-22 00:00:00'
          AND r.name IS DISTINCT FROM (
              d.name || ' - ' || s.name || ' - ' ||
              to_char(r.measurement_time, 'YYYY-MM-DD HH24:MI:SS')
          )
    """)
    staged_count = cr.rowcount
    _logger.info(
        'Staged %d readings with out-of-sync name for UTC normalization.',
        staged_count,
    )

    # 3. Remove any older row (< 2026-10-22) that might still occupy a target
    #    canonical UTC name for the same sensor/timestamp.
    cr.execute("""
        DELETE FROM mdm_measurement_device_sensor_reading old_r
        USING mdm_measurement_device_sensor_reading new_r,
              mdm_measurement_device_sensor s,
              mdm_measurement_device d
        WHERE new_r.name LIKE '__tmp_reading_name__%%'
          AND new_r.sensor_id = s.id
          AND d.id = s.device_id
          AND old_r.id <> new_r.id
          AND old_r.name = (
              d.name || ' - ' || s.name || ' - ' ||
              to_char(new_r.measurement_time, 'YYYY-MM-DD HH24:MI:SS')
          )
    """)
    if cr.rowcount:
        _logger.info(
            'Removed %d conflicting reading rows occupying canonical names.',
            cr.rowcount,
        )

    # 4. Set the canonical UTC name on all staged readings.
    cr.execute("""
        UPDATE mdm_measurement_device_sensor_reading r
        SET name = (
            d.name || ' - ' || s.name || ' - ' ||
            to_char(r.measurement_time, 'YYYY-MM-DD HH24:MI:SS')
        )
        FROM mdm_measurement_device_sensor s
        JOIN mdm_measurement_device d ON d.id = s.device_id
        WHERE r.sensor_id = s.id
          AND r.name LIKE '__tmp_reading_name__%%'
    """)
    _logger.info(
        'Normalized %d reading names to UTC format.',
        cr.rowcount,
    )
    _logger.info('mdm_sensor_management post-migration 10.0.1.2.1 completed')
