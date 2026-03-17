# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    MODULE = 'remotecontrol_inelcom'

    # Fix "Get devices (plan)" action: remove +timedelta(days=1) from
    # initial_date calculation in BOTH plan loops (sensors_plan and
    # location_variables_plan). Safe because upsert handles duplicates.

    new_code = """\
Remote = self.remote_id
Sensor = env['mdm.measurement.device.sensor']
Reading = env['mdm.measurement.device.sensor.reading']
today_str = fields.Date.today()
condition = [
    ('remotecontrol_params', '!=', False),
    ('device_id.remotecontrol_id', '=', Remote.id)
]
if selected_device_ids:
    condition.append(('device_id', 'in', selected_device_ids))
sensors = Sensor.search(condition)
last_readings_map = {}
if sensors:
    readings = Reading.search(
        [('sensor_id', 'in', sensors.ids), ('active', '=', True)],
        order='sensor_id ASC, measurement_time DESC'
    )
    for r in readings:
        sid = r.sensor_id.id
        if sid not in last_readings_map:
            last_readings_map[sid] = r.measurement_time
plan = []
for sensor in sensors:
    device = sensor.device_id
    try:
        sensor_cfg = json.loads(sensor.remotecontrol_params or '{}') or {}
    except Exception:
        sensor_cfg = {}
    try:
        device_cfg = json.loads(device.remotecontrol_params or '{}') or {}
    except Exception:
        device_cfg = {}
    route = sensor_cfg.get('route')
    sensor_id_param = device_cfg.get('device_id')
    if not (route and sensor_id_param):
        continue
    last_reading_time = last_readings_map.get(sensor.id)
    start_dev = device_cfg.get('start_date')
    start_sensor = sensor_cfg.get('start_date')
    if last_reading_time:
        try:
            last_dt = fields.Datetime.from_string(last_reading_time)
            initial_date = fields.Date.to_string(last_dt)
        except Exception:
            initial_date = str(last_reading_time)[:10]
    elif start_dev:
        initial_date = start_dev[:10]
    elif start_sensor:
        initial_date = start_sensor[:10]
    else:
        initial_date = '%s-01-01' % today_str[:4]
    if isinstance(initial_date, unicode):
        initial_date = initial_date.encode('utf-8')
    plan.append({
        'sensor_id': sensor.id,
        'sensor_id_param': sensor_id_param,
        'route': route,
        'device_id': device.id,
        'initial_date': initial_date
    })
bag['sensors_plan'] = plan

location_variables_plan = []
location_condition = [
    ('remotecontrol_params', '!=', False),
    ('device_id.remotecontrol_id', '=', Remote.id)
]
if selected_device_ids:
    location_condition.append(('device_id', 'in', selected_device_ids))
location_sensors = Sensor.search(location_condition)

for sensor in location_sensors:
    device = sensor.device_id
    try:
        sensor_cfg = json.loads(sensor.remotecontrol_params or '{}') or {}
    except Exception:
        sensor_cfg = {}
    try:
        device_cfg = json.loads(device.remotecontrol_params or '{}') or {}
    except Exception:
        device_cfg = {}

    variable_id = sensor_cfg.get('variable_id')
    if not variable_id:
        continue

    last_reading_time = last_readings_map.get(sensor.id)
    start_dev = device_cfg.get('start_date')
    start_sensor = sensor_cfg.get('start_date')

    if last_reading_time:
        try:
            last_dt = fields.Datetime.from_string(last_reading_time)
            initial_date = fields.Date.to_string(last_dt)
        except Exception:
            initial_date = str(last_reading_time)[:10]
    elif start_sensor:
        initial_date = start_sensor[:10]
    elif start_dev:
        initial_date = start_dev[:10]
    else:
        initial_date = '%s-01-01' % today_str[:4]

    if isinstance(initial_date, unicode):
        initial_date = initial_date.encode('utf-8')

    location_variables_plan.append({
        'sensor_id': sensor.id,
        'variable_id': variable_id,
        'device_id': device.id,
        'initial_date': initial_date
    })

bag['location_variables_plan'] = location_variables_plan
"""

    xmlid = '%s.remotecontrol_inelcom_action_get_devices' % MODULE
    action = env.ref(xmlid, raise_if_not_found=False)
    if action:
        action.write({'code': new_code})
