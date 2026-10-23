# -*- coding: utf-8 -*-
# Copyright 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import SUPERUSER_ID, api


_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    _logger.info(
        'law_water_quality_remotecontrol_salz post-migration '
        '10.0.1.1.1 started'
    )
    env = api.Environment(cr, SUPERUSER_ID, {})
    xmlid = (
        'law_water_quality_remotecontrol.'
        'wua_cron_import_pressure_measurements_global_action'
    )
    cron = env.ref(xmlid, raise_if_not_found=False)
    if cron:
        cron.write({'daylight_saving_time_resistant': True})
        _logger.info(
            'Updated daylight_saving_time_resistant on cron %s.', xmlid
        )
    else:
        _logger.info('Cron %s not found.', xmlid)
    _logger.info(
        'law_water_quality_remotecontrol_salz post-migration '
        '10.0.1.1.1 completed'
    )

