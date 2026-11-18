# -*- coding: utf-8 -*-
# Copyright 2026 Moval Agroingenieria
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

"""Guarantee new noupdate action/procedure exist after upgrading old databases.

New XML IDs usually load on upgrade, but this fallback does not rely on that
behavior. Existing records and user customizations are left untouched.
"""

import logging
import os
from xml.etree import ElementTree

from odoo import SUPERUSER_ID, api


_logger = logging.getLogger(__name__)
MODULE = 'remotecontrol_hidroconta'


def _ensure_record(env, model, xml_name, vals):
    data = env['ir.model.data'].search([
        ('module', '=', MODULE), ('name', '=', xml_name)], limit=1)
    if data:
        record = env[model].browse(data.res_id)
        if record.exists():
            return record
        # An XMLID must never be left pointing at a deleted record.
        data.unlink()
    record = env[model].create(vals)
    env['ir.model.data'].create({
        'module': MODULE,
        'name': xml_name,
        'model': model,
        'res_id': record.id,
        'noupdate': True,
    })
    _logger.info('Created %s %s (id=%s)', model, xml_name, record.id)
    return record


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    remote = env.ref(MODULE + '.remotecontrol_hidroconta')
    login = env.ref(MODULE + '.remotecontrol_hidroconta_action_login')
    plan = env.ref(MODULE + '.remotecontrol_hidroconta_action_build_sensor_plan')
    path = os.path.normpath(os.path.join(
        os.path.dirname(__file__), '..', '..', 'data', 'data_last_reading.xml'))
    xml_root = ElementTree.parse(path).getroot()
    xml_action = xml_root.find(
        ".//record[@id='remotecontrol_hidroconta_action_get_last_reading']")
    if xml_action is None:
        raise ValueError('Missing Get Last Reading action definition in XML')
    xml_code = xml_action.find("field[@name='code']")
    if xml_code is None or not xml_code.text:
        raise ValueError('Missing Get Last Reading Python code in XML')

    action = _ensure_record(env, 'remotecontrol.action',
        'remotecontrol_hidroconta_action_get_last_reading', {
            'name': 'Hidroconta: Get Last Reading',
            'remote_id': remote.id,
            'sequence': 50,
            'active': True,
            'rate_limit_seconds': 0.0,
            'max_retries': 1,
            'backoff': 1.6,
            'readonly': True,
            'code': xml_code.text.strip(),
        })
    procedure = _ensure_record(env, 'remotecontrol.procedure',
        'remotecontrol_hidroconta_procedure_get_last_reading', {
            'name': 'Hidroconta: Get Last Reading',
            'remote_id': remote.id,
            'sequence': 30,
            'active': True,
            'schedule_cron': False,
            'readonly': True,
            'procedure_for_readings': False,
            'interval_number': 15,
            'interval_type': 'minutes',
        })
    for xmlid, name, act, seq in [
            ('remotecontrol_hidroconta_step_last_reading_10_login', 'Login', login, 10),
            ('remotecontrol_hidroconta_step_last_reading_20_plan', 'Build Sensor Plan', plan, 20),
            ('remotecontrol_hidroconta_step_last_reading_30_readings', 'Get Last Reading', action, 30)]:
        _ensure_record(env, 'remotecontrol.step', xmlid, {
            'name': name,
            'procedure_id': procedure.id,
            'action_id': act.id,
            'sequence': seq,
        })
    _logger.info('Hidroconta Get Last Reading action and procedure verified')
