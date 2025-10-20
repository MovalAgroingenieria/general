# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Update action: 4eGrowth: Get devices (plan)
    new_code_get_devices = """
# Action A: build sensors plan (robust JSON parsing)
Sensor = env['mdm.measurement.device.sensor']
Reading = env['mdm.measurement.device.sensor.reading']
today_str = fields.Date.today()
condition = [('remotecontrol_params','!=',False)]
if selected_device_ids:
    condition.append(('device_id', 'in', selected_device_ids))
else:
    condition.append(('device_id','!=',False))
sensors = Sensor.search(condition)
# Optimize: build map of sensor_id -> most recent reading (single query)
last_readings_map = {}
if sensors:
    sensor_ids = [s.id for s in sensors]
    cr = env.cr
    cr.execute(
        'SELECT DISTINCT ON (sensor_id) sensor_id, measurement_time '
        'FROM mdm_measurement_device_sensor_reading '
        'WHERE sensor_id IN %s '
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
    parameter = (sensor_cfg.get('parameter') or '').strip()
    parameter_value = sensor_cfg.get('parameter_value')
    parameter_group = (sensor_cfg.get('group') or '').strip()
    parameter_key = (sensor_cfg.get('key') or '').strip()
    if parameter and parameter_value not in (None,'') and parameter_group and parameter_key:
        try:
            device_cfg = json.loads(device.remotecontrol_params or '{}') or {}
        except Exception:
            device_cfg = {}
        growth_id = (device_cfg.get('growth_id') or '').strip()
        if growth_id:
            # Retrieve last_reading from map (no query per sensor)
            last_reading_time = last_readings_map.get(sensor.id)
            if last_reading_time:
                try:
                    initial_date = fields.Date.to_string(last_reading_time.date())
                except Exception:
                    initial_date = str(last_reading_time)[:10]
            else:
                start_cfg = (sensor_cfg.get('start_date') or device_cfg.get('start_date'))
                if start_cfg:
                    initial_date = start_cfg[:10]
                else:
                    year_str = today_str[:4]
                    initial_date = '%s-01-01' % year_str
            plan.append({
                'sensor_id': sensor.id,
                'device_id': device.id,
                'growth_id': growth_id,
                'parameter': parameter,
                'parameter_value': parameter_value,
                'parameter_group': parameter_group,
                'parameter_key': parameter_key,
                'initial_date': initial_date,
            })
bag['sensors_plan'] = plan
"""
    xml_id_get_devices = 'remotecontrol_4egrowth_action_get_devices'
    try:
        action_get_devices = env.ref(
            'remotecontrol_4egrowth.%s' % xml_id_get_devices)
        action_get_devices.write({'code': new_code_get_devices})
    except Exception:
        pass
