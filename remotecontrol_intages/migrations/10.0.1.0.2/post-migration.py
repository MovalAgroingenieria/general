# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    MODULE = 'remotecontrol_intages'

    # Fix "Build plan" action: remove +timedelta(days=1) from
    # initial_date calculation. Safe because upsert handles duplicates.

    new_code = """\
import json
from datetime import timedelta
Remote = self.remote_id
Sensor = env['mdm.measurement.device.sensor']
Reading = env['mdm.measurement.device.sensor.reading']
today_str = fields.Date.today()
condition = [
    ('remotecontrol_params', '!=', False),
    ('device_id.remotecontrol_id', '=', Remote.id),
]
if selected_device_ids:
    condition.append(('device_id', 'in', selected_device_ids))
sensors = Sensor.search(condition)
sensor_ids = [s.id for s in sensors]
last_readings_map = {}
if sensors:
    cr = env.cr
    cr.execute(
        'SELECT DISTINCT ON (sensor_id) sensor_id, measurement_time '
        'FROM mdm_measurement_device_sensor_reading '
        'WHERE sensor_id IN %s AND active = TRUE '
        'ORDER BY sensor_id, measurement_time DESC',
        (tuple(sensor_ids),)
    )
    for sid, mtime in cr.fetchall():
        last_readings_map[sid] = mtime
plan = []
for sensor in sensors:
    device = sensor.device_id
    try:
        scfg = json.loads(sensor.remotecontrol_params or '{}') or {}
    except:
        scfg = {}
    try:
        dcfg = json.loads(device.remotecontrol_params or '{}') or {}
    except:
        dcfg = {}
    station_name = dcfg.get('device_id' or '')
    sensor_name = scfg.get('sensor_id' or '')
    start_cfg = scfg.get('start_date') or dcfg.get('start_date')
    last_m = last_readings_map.get(sensor.id)
    if last_m:
        try:
            initial_date = fields.Date.to_string(
                fields.Datetime.from_string(last_m)
            )
        except:
            initial_date = str(last_m)[:10]
    else:
        if start_cfg:
            initial_date = start_cfg[:10]
        else:
            year = today_str[:4]
            initial_date = '%s-01-01' % year
    stype = scfg.get('type', '').strip().lower()
    if stype not in ('pressure', 'flow', 'volume'):
        stype = 'unknown'
    plan.append({
        'sensor_id': sensor.id,
        'device_id': device.id,
        'station_name': station_name,
        'sensor_type': stype,
        'sensor_name': sensor_name,
        'initial_date': initial_date,
    })
bag['intages_plan'] = plan
bag['intages_plan_count'] = len(plan)
"""

    xmlid = '%s.remotecontrol_intages_action_build_plan' % MODULE
    action = env.ref(xmlid, raise_if_not_found=False)
    if action:
        action.write({'code': new_code})
