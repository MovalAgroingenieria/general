# -*- coding: utf-8 -*-
# Copyright 2026 Moval Agroingenieria
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

"""Complete Hidroconta last-reading installation settings from WUA, if safe.

This migration is deliberately optional: missing/incomplete WUA settings or an
existing manual configuration must never prevent upgrading the module.
"""

import json
import logging

from odoo import SUPERUSER_ID, api


_logger = logging.getLogger(__name__)
_REMOTE_XMLID = 'remotecontrol_hidroconta.remotecontrol_hidroconta'
_WUA_MODEL = 'wua.irrigation.configuration'
_WUA_MODULE = 'wua_remotecontrol_rest_hidroconta_demeter'

try:
    _string_types = (basestring,)
except NameError:
    _string_types = (str,)


def _migrate_connection_params(env):
    remote = env.ref(_REMOTE_XMLID, raise_if_not_found=False)
    if not remote or not remote.exists():
        _logger.warning('Hidroconta: telecontrol not found; skipping settings.')
        return

    raw_params = remote.connection_params
    if not raw_params:
        _logger.warning('Hidroconta: empty connection_params; unchanged.')
        return

    try:
        params = json.loads(raw_params)
    except (ValueError, TypeError):
        _logger.warning('Hidroconta: invalid connection_params JSON; unchanged.')
        return

    if not isinstance(params, dict):
        _logger.warning('Hidroconta: connection_params is not an object; unchanged.')
        return

    # Never overwrite (or silently complete) a manual installation mapping.
    if 'installation_code' in params or 'installation_id' in params:
        _logger.info('Hidroconta: installation settings already exist; unchanged.')
        return

    wua_installed = env['ir.module.module'].search([
        ('name', '=', _WUA_MODULE),
        ('state', 'in', ['installed', 'to upgrade']),
    ], limit=1)
    if not wua_installed:
        _logger.info('Hidroconta: WUA integration is not installed; unchanged.')
        return

    values = env['ir.values'].sudo()
    code = values.get_default(_WUA_MODEL, 'installation_code_hidroconta')
    identifier = values.get_default(_WUA_MODEL, 'installation_identifier')

    if not isinstance(code, _string_types) or not code.strip():
        _logger.warning('Hidroconta: missing WUA installation code; unchanged.')
        return
    code = code.strip()
    if code.lower().startswith('i='):
        _logger.warning('Hidroconta: unexpected WUA installation code format; unchanged.')
        return

    try:
        installation_id = int(str(identifier).strip())
    except (TypeError, ValueError):
        _logger.warning('Hidroconta: invalid WUA installation ID; unchanged.')
        return
    if installation_id <= 0:
        _logger.warning('Hidroconta: missing WUA installation ID; unchanged.')
        return

    # Preserve existing credentials, flags and any manually configured settings.
    params['installation_code'] = code
    params['installation_id'] = installation_id
    params.setdefault('last_reading_audit', False)
    remote.write({
        'connection_params': json.dumps(
            params, indent=2, sort_keys=True, ensure_ascii=False),
    })
    _logger.info('Hidroconta: installation mapping configured from WUA.')


def migrate(cr, version):
    if not version:
        return
    # A failed write must be rolled back before the upgrade can continue.
    try:
        with cr.savepoint():
            env = api.Environment(cr, SUPERUSER_ID, {})
            _migrate_connection_params(env)
    except Exception as exc:
        # Do not log the exception text: it could contain connection parameters.
        _logger.warning(
            'Hidroconta: optional installation migration skipped after %s; '
            'module upgrade may continue.', exc.__class__.__name__)
