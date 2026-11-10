# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

PARAM_API_KEY = 'board_grafana_integration.api_key'


def migrate(cr, version):
    if not version:
        return
    _logger.info(
        'board_grafana_integration post-migration 10.0.1.2.0 started')
    env = api.Environment(cr, SUPERUSER_ID, {})
    values_model = env['ir.values']
    param_model = env['ir.config_parameter']
    api_key = values_model.get_default(
        'board.grafana.configuration', 'grafana_api_key')
    env['board.grafana.configuration']._ensure_grafana_api_key_param()
    if api_key and not param_model.get_param(PARAM_API_KEY):
        param_model.set_param(
            PARAM_API_KEY, api_key, groups=['base.group_system'])
        _logger.info('Grafana API key moved to the system parameter %s',
                     PARAM_API_KEY)
    # Removed even when empty: it was readable by every internal user
    values_model.search([
        ('model', '=', 'board.grafana.configuration'),
        ('name', '=', 'grafana_api_key'),
        ('key', '=', 'default'),
    ]).unlink()
    _logger.info(
        'board_grafana_integration post-migration 10.0.1.2.0 completed')
