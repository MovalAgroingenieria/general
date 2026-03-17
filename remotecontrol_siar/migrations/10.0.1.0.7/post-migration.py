# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    MODULE = 'remotecontrol_siar'

    # Fix "Get devices (plan)" action: remove +timedelta(days=1) from
    # start_date calculation. Safe because upsert handles duplicates.

    new_code = """\
# Action A: build sensors plan
import json
from datetime import datetime, timedelta
plan = []
siar_token = bag.get('siar_token')
if not siar_token:
    raise Exception('No SiAR token found. Token must be obtained first.')
condition = []
if selected_device_ids:
    condition.append(('id', 'in', selected_device_ids))
else:
    condition.append(('remotecontrol_id', '=', self.remote_id.id))
devices = env['mdm.measurement.device'].search(condition)
if not devices:
    raise Exception('There is no SiAR device.')
yesterday_str = (datetime.strptime(fields.Date.today(), "%Y-%m-%d") -
                 timedelta(days=1)).strftime("%Y-%m-%d")
default_initial_date = '%s-%s-01' % (yesterday_str[:4], yesterday_str[5:7])
default_final_date = yesterday_str
# Optimize: collect all sensor IDs first to avoid N+1 queries
all_sensor_ids = []
for device in (devices or []):
    all_sensor_ids.extend([s.id for s in device.sensor_ids])
# Build map of sensor_id -> most recent reading (single query)
last_readings_map = {}
if all_sensor_ids:
    cr = env.cr
    cr.execute(
        'SELECT DISTINCT ON (sensor_id) sensor_id, measurement_time '
        'FROM mdm_measurement_device_sensor_reading '
        'WHERE sensor_id IN %s AND active = TRUE '
        'ORDER BY sensor_id, measurement_time DESC',
        (tuple(all_sensor_ids),)
    )
    for row in cr.fetchall():
        last_readings_map[row[0]] = row[1]
# Now iterate devices/sensors using the map
for device in (devices or []):
    try:
        device_cfg = json.loads(device.remotecontrol_params or '{}') or {}
    except Exception:
        device_cfg = {}
    station = (device_cfg.get('station') or '').strip()
    if not station:
        continue
    for sensor in (device.sensor_ids or []):
        start_date = (device_cfg.get('start_date') or '').strip()
        if not start_date:
            start_date = default_initial_date
        try:
            sensor_cfg = json.loads(sensor.remotecontrol_params or '{}') or {}
        except Exception:
            sensor_cfg = {}
        magnitude = (sensor_cfg.get('magnitude') or '').strip()
        if not magnitude:
            continue
        sensor_plan = {
            'siar_token': siar_token,
            'device_id': device.id,
            'sensor_id': sensor.id,
            'station': station,
            'magnitude': magnitude
        }
        # Retrieve last_reading from map (no query per sensor)
        last_reading_time = last_readings_map.get(sensor.id)
        if last_reading_time:
            try:
                # last_reading_time comes as string from SQL execute
                start_date = fields.Date.to_string(
                    fields.Datetime.from_string(last_reading_time))
            except Exception:
                start_date = default_initial_date
        sensor_plan['initial_date'] = start_date
        end_date = default_final_date
        if end_date < start_date:
            end_date = start_date
        sensor_plan['final_date'] = end_date
        plan.append(sensor_plan)
bag['sensors_plan'] = plan
"""

    xmlid = '%s.remotecontrol_siar_action_get_devices' % MODULE
    action = env.ref(xmlid, raise_if_not_found=False)
    if action:
        action.write({'code': new_code})
