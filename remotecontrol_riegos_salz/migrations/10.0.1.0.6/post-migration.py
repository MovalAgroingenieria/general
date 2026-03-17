# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    MODULE = 'remotecontrol_riegos_salz'

    # Fix "Get devices (plan)" action: remove +timedelta(days=1) from
    # start_date calculation. Safe because upsert handles duplicates.

    new_code = """\
from datetime import datetime

Remote = self.remote_id
Sensor = env['mdm.measurement.device.sensor']
Reading = env['mdm.measurement.device.sensor.reading']
today_str = fields.Date.today()
condition = [
    ('remotecontrol_params','!=',False),
    ('device_id.remotecontrol_id', '=', Remote.id)
]
if selected_device_ids:
    condition.append(('device_id', 'in', selected_device_ids))
sensors = Sensor.search(condition)
# Optimize: build map of sensor_id -> most recent reading (single query)
last_readings_map = {}
if sensors:
    sensor_ids = [s.id for s in sensors]
    cr = env.cr
    cr.execute(
        'SELECT DISTINCT ON (sensor_id) sensor_id, measurement_time '
        'FROM mdm_measurement_device_sensor_reading '
        'WHERE sensor_id IN %s AND active = TRUE '
        'ORDER BY sensor_id, measurement_time DESC',
        (tuple(sensor_ids),)
    )
    for row in cr.fetchall():
        last_readings_map[row[0]] = row[1]
# Now iterate sensors using the map
plan = []
for sensor in sensors:
    device = sensor.device_id
    try:
        sensor_cfg = json.loads(sensor.remotecontrol_params or '{}') or {}
    except Exception:
        sensor_cfg = {}
    sensor_id_value = sensor_cfg.get('id')
    if isinstance(sensor_id_value, int):
        try:
            device_cfg = json.loads(device.remotecontrol_params or '{}') or {}
        except Exception:
            device_cfg = {}
        # Retrieve last_reading from map (no query per sensor)
        last_reading_time = last_readings_map.get(sensor.id)
        if last_reading_time:
            try:
                last_dt = fields.Datetime.from_string(
                    last_reading_time)
                start_date = last_dt.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                start_date = str(last_reading_time)
        else:
            start_cfg = device_cfg.get('start_date')
            if start_cfg:
                s = start_cfg.strip().replace('/', '-')
                if len(s) == 10:
                    s = s + ' 00:00:00'
                try:
                    dt_cfg = datetime.strptime(s, '%Y-%m-%d %H:%M:%S')
                    start_date = dt_cfg.strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    start_date = s
            else:
                year_str = today_str[:4]
                s2 = '%s-01-01 00:00:00' % year_str
                try:
                    dt_y = datetime.strptime(s2, '%Y-%m-%d %H:%M:%S')
                    start_date = dt_y.strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    start_date = s2
        plan.append({
            'sensor_id': sensor.id,
            'device_id': device.id,
            'sensor_id_value': sensor_id_value,
            'start_date': str(start_date),
        })
bag['sensors_plan'] = plan
"""

    xmlid = '%s.remotecontrol_riegos_salz_action_get_devices' % MODULE
    action = env.ref(xmlid, raise_if_not_found=False)
    if action:
        action.write({'code': new_code})
