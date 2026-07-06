# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Pre-migration: Rename existing UoM records that conflict with new ones
    """
    # UoM names to check and rename if they exist
    uom_names = ['m³', 'L/s', 'm.c.a', 'm']
    _logger.info('Checking for existing UoM records to rename...')
    for uom_name in uom_names:
        # Check if a UoM with this name already exists
        existing_uom = False
        try:
            cr.savepoint()
            cr.execute("""
                SELECT id, name, readonly
                FROM mdm_measurement_device_sensor_uom
                WHERE name = %s
            """, (uom_name,))
            existing_uom = cr.fetchone()
        except Exception:
            cr.rollback()
            break
        if existing_uom:
            uom_id, old_name, is_readonly = existing_uom
            new_name = '%s (old)' % old_name
            _logger.info(
                'Found existing UoM "%s" (id: %s, readonly: %s). '
                'Renaming to "%s"',
                old_name, uom_id, is_readonly, new_name,
            )
            # Update the name even if it's readonly
            cr.execute("""
                UPDATE mdm_measurement_device_sensor_uom
                SET name = %s, readonly = False
                WHERE id = %s
            """, (new_name, uom_id))
            _logger.info('Successfully renamed UoM %s to %s', uom_id, new_name)
    _logger.info('Pre-migration completed for UoM records')
