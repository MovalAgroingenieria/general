# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    """Set procedure_for_readings = True and patch action codes."""
    try:
        procedure = env.ref('remotecontrol_odins.remotecontrol_odins_'
                            'procedure_daily_sync')
        procedure.write({'procedure_for_readings': True})
    except Exception:
        pass
    # Patch action: remotecontrol_odins_action_get_device
    try:
        action = env.ref('remotecontrol_odins.remotecontrol_odins_'
                         'action_get_device')
        action.write({
            'code': '''
# Action: build sensors plan (robust JSON parsing with SQL optimization)
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
    sensor_parameter = (sensor_cfg.get('sensor_id') or '').strip()
    if sensor_parameter not in (None,''):
        try:
            device_cfg = json.loads(device.remotecontrol_params or '{}') or {}
        except Exception:
            device_cfg = {}
        device_parameter = (device_cfg.get('device_id') or '').strip()
        if device_parameter:
            # Retrieve last_reading from map (no query per sensor)
            last_reading_time = last_readings_map.get(sensor.id)
            if last_reading_time:
                try:
                    initial_date = fields.Date.to_string(
                        fields.Datetime.from_string(last_reading_time) +
                        timedelta(days=1))
                except Exception:
                    initial_date = str(last_reading_time)[:10]
            else:
                start_cfg = (sensor_cfg.get('start_date') or device_cfg.get(
                    'start_date'))
                if start_cfg:
                    initial_date = start_cfg[:10]
                else:
                    year_str = today_str[:4]
                    initial_date = '%s-01-01' % year_str
            level = sensor_cfg.get('level', '')
            plan.append({
                'sensor_id': sensor.id,
                'device_id': device.id,
                'sensor_parameter': sensor_parameter,
                'device_parameter': device_parameter,
                'level': level,
                'initial_date': initial_date,
            })
bag['sensors_plan'] = plan
''',
        })
    except Exception:
        pass
