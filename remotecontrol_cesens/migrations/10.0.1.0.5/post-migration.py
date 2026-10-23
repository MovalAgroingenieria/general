# -*- coding: utf-8 -*-
# Copyright 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import SUPERUSER_ID, api


_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    _logger.info('remotecontrol_cesens post-migration 10.0.1.0.5 started')
    env = api.Environment(cr, SUPERUSER_ID, {})
    procedures = env['remotecontrol.procedure'].with_context(
        active_test=False
    ).search([('cron_id', '!=', False)])
    crons = procedures.mapped('cron_id')
    if crons:
        crons.write({'daylight_saving_time_resistant': True})
        _logger.info(
            'Updated daylight_saving_time_resistant on %d procedure crons.',
            len(crons),
        )
    else:
        _logger.info('No procedure crons found to update.')
    _logger.info('remotecontrol_cesens post-migration 10.0.1.0.5 completed')

