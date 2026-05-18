# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Post-migration: Initialize measurement_transformation, raw_value,
    and range validation fields for existing records.
    """
    _logger.info('Initializing transformation fields for existing data...')
    cr.execute("""
        UPDATE mdm_measurement_device_sensor
        SET measurement_transformation = '$',
            measurement_transformation_type = 'arithmetic'
        WHERE measurement_transformation IS NULL
           OR measurement_transformation_type IS NULL
    """)
    cr.execute("""
        UPDATE mdm_measurement_device_sensor_reading
        SET raw_value = value,
            measurement_transformation = '$',
            measurement_transformation_type = 'arithmetic'
        WHERE raw_value IS NULL
    """)
    cr.execute("""
        UPDATE mdm_measurement_device_sensor
        SET has_range_validation = false
        WHERE has_range_validation IS NULL
    """)
    cr.execute("""
        UPDATE mdm_measurement_device_sensor_type
        SET has_range_validation = false
        WHERE has_range_validation IS NULL
    """)
    cr.execute("""
        UPDATE mdm_measurement_device_sensor_reading
        SET range_status = 'unchecked',
            is_out_of_range = false
        WHERE range_status IS NULL
    """)
    _logger.info('Migration completed: transformation and range fields '
                 'initialized.')
