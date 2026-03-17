# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    MODULE = 'remotecontrol_icc_pro'

    # Fix "Build sensor plan" action: remove +timedelta(days=1) from
    # initial_date calculation. Safe because upsert handles duplicates.

    new_code = """\
# Build sensor plan from device/sensor remotecontrol_params
Remote = self.remote_id
Sensor = env['mdm.measurement.device.sensor']
Reading = env['mdm.measurement.device.sensor.reading']
today_str = fields.Date.today()

# Get all sensors with remotecontrol_params configured for THIS remote control
condition = [
    ('remotecontrol_params', '!=', False),
    ('device_id.remotecontrol_id', '=', Remote.id),
    ('active', '=', True),
]
if selected_device_ids:
    condition.append(('device_id', 'in', selected_device_ids))
sensors = Sensor.search(condition)

# Build map of sensor_id -> most recent reading (single query optimization)
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

# Build execution plan
sensor_plan = []

for sensor in sensors:
    device = sensor.device_id

    # Parse sensor configuration
    try:
        sensor_cfg = json.loads(sensor.remotecontrol_params or '{}') or {}
    except Exception:
        sensor_cfg = {}

    # Parse device configuration
    try:
        device_cfg = json.loads(device.remotecontrol_params or '{}') or {}
    except Exception:
        device_cfg = {}

    # Get meter_id from sensor or device config
    meter_id = sensor_cfg.get('meter_id') or device_cfg.get('meter_id')
    value_field = sensor_cfg.get('value_field', 'AccVolume')  # Default to totalizer

    if not meter_id:
        continue

    # Determine initial date for this sensor
    last_reading_time = last_readings_map.get(sensor.id)
    if last_reading_time:
        try:
            initial_date = fields.Date.to_string(
                fields.Datetime.from_string(last_reading_time))
        except Exception:
            initial_date = str(last_reading_time)[:10]
    else:
        # Use start_date from sensor config or device config, or Jan 1 of current year
        start_cfg = sensor_cfg.get('start_date') or device_cfg.get('start_date')
        if start_cfg:
            initial_date = start_cfg[:10]
        else:
            year_str = today_str[:4]
            initial_date = '%s-01-01' % year_str

    plan_item = {
        'odoo_sensor_id': sensor.id,
        'odoo_device_id': device.id,
        'meter_id': meter_id,
        'value_field': value_field,
        'start_date': initial_date
    }
    sensor_plan.append(plan_item)

bag['sensor_plan'] = sensor_plan
bag['plan_count'] = len(sensor_plan)

result = 'Built sensor plan with %d sensors' % len(sensor_plan)
"""

    xmlid = '%s.remotecontrol_icc_pro_action_build_sensor_plan' % MODULE
    action = env.ref(xmlid, raise_if_not_found=False)
    if action:
        action.write({'code': new_code})
