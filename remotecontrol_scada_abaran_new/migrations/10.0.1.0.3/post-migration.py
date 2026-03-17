# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    MODULE = 'remotecontrol_scada_abaran_new'

    # Fix "Get devices (plan)" action: remove +timedelta(days=1) from
    # initial_date calculation. Safe because upsert handles duplicates.

    new_code = """\
# Build sensors plan from device and sensor remotecontrol_params
Remote = self.remote_id
Device = env['mdm.measurement.device']
Sensor = env['mdm.measurement.device.sensor']
Reading = env['mdm.measurement.device.sensor.reading']
today_str = fields.Date.today()

# Get all devices with remotecontrol_params configured for THIS remote control
device_domain = [
    ('remotecontrol_params', '!=', False),
    ('remotecontrol_id', '=', Remote.id),
]
if selected_device_ids:
    device_domain.append(('id', 'in', selected_device_ids))
devices = Device.search(device_domain)

# Build map of sensor_id -> most recent reading (single query optimization)
all_sensors = Sensor.search([('device_id', 'in', devices.ids)])
last_readings_map = {}
if all_sensors:
    sensor_ids = [s.id for s in all_sensors]
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
plan = []
for device in devices:
    # Parse device configuration
    try:
        device_cfg = json.loads(device.remotecontrol_params or '{}') or {}
    except Exception:
        device_cfg = {}

    # Get table name from device config
    table_name = device_cfg.get('table_name')
    if not table_name:
        continue

    # Get all sensors for this device with remotecontrol_params
    sensors = Sensor.search([
        ('device_id', '=', device.id),
        ('remotecontrol_params', '!=', False)
    ])

    for sensor in sensors:
        # Parse sensor configuration
        try:
            sensor_cfg = json.loads(sensor.remotecontrol_params or '{}') or {}
        except Exception:
            sensor_cfg = {}

        # Get configuration from sensor
        datetime_column = sensor_cfg.get('datetime_column')
        value_column = sensor_cfg.get('value_column')

        # Validate required parameters
        if not datetime_column or not value_column:
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
            # Use start_date from sensor config or Jan 1 of current year
            start_cfg = sensor_cfg.get('start_date')
            if start_cfg:
                initial_date = start_cfg[:10]
            else:
                year_str = today_str[:4]
                initial_date = '%s-01-01' % year_str

        plan.append({
            'sensor_id': sensor.id,
            'device_id': device.id,
            'table_name': table_name,
            'datetime_column': datetime_column,
            'value_column': value_column,
            'initial_date': initial_date,
        })

bag['sensors_plan'] = plan
bag['plan_count'] = len(plan)
"""

    xmlid = '%s.remotecontrol_scada_abaran_new_action_get_devices' % MODULE
    action = env.ref(xmlid, raise_if_not_found=False)
    if action:
        action.write({'code': new_code})
