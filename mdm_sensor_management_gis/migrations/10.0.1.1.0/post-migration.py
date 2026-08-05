# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    categories = env['mdm.measurement.device.category'].search([])
    updated = 0
    for category in categories:
        if not category.legend_symbology:
            continue
        try:
            legend = json.loads(category.legend_symbology)
        except (ValueError, TypeError):
            continue
        if not isinstance(legend, list) or not legend:
            continue
        first_entry = legend[0]
        if isinstance(first_entry, dict) and not first_entry.get('name'):
            first_entry['name'] = 'Normal'
            category.legend_symbology = json.dumps(legend, indent=2)
            updated += 1
    _logger.info(
        'mdm_sensor_management_gis: added default "name" to %s category '
        'legends.', updated)
