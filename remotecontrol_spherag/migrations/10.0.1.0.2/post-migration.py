# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    MODULE = 'remotecontrol_spherag'

    # Fix "Get devices (plan)" action: remove +timedelta(days=1) from
    # initial_date calculation. Safe because upsert handles duplicates.

    new_code = """\
Remote = self.remote_id
Sensor = env['mdm.measurement.device.sensor']
today_str = fields.Date.today()

condition = [
    ('remotecontrol_params', '!=', False),
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

# Build plan for each sensor
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

# Get configuration with validation
    system_id = device_cfg.get('system_id')
    imei = device_cfg.get('imei')
    atlas_element_id = sensor_cfg.get('atlas_element_id')
    chart_type = sensor_cfg.get('chart_type')
    data_type = sensor_cfg.get('data_type', 'sensor_data')  # Default to sensor_data
    data_array_index = sensor_cfg.get('data_array_index', 0)  # Default to first array
    value_index = sensor_cfg.get('value_index', 0)  # Default to first position
    start_cfg = sensor_cfg.get('start_date') or device_cfg.get('start_date')

    # Validate all required fields are present and not None/empty
    if not system_id or not imei or not atlas_element_id or not chart_type:
        # Log warning about missing configuration
        continue

    # Determine initial date
    last_reading_time = last_readings_map.get(sensor.id)
    if last_reading_time:
        try:
            initial_date = fields.Date.to_string(
                fields.Datetime.from_string(last_reading_time)
            )
        except Exception:
            initial_date = str(last_reading_time)[:10]
    elif start_cfg:
        initial_date = start_cfg[:10]
    else:
        year_str = today_str[:4]
        initial_date = '%s-01-01' % year_str

    if isinstance(initial_date, unicode):
        initial_date = initial_date.encode('utf-8')

    plan.append({
        'sensor_id': sensor.id,
        'device_id': device.id,
        'system_id': system_id,
        'imei': imei,
        'atlas_element_id': atlas_element_id,
        'chart_type': chart_type,
        'data_type': data_type,
        'data_array_index': data_array_index,
        'value_index': value_index,
        'initial_date': initial_date
    })

bag['sensors_plan'] = plan
"""

    xmlid = '%s.remotecontrol_spherag_action_get_devices' % MODULE
    action = env.ref(xmlid, raise_if_not_found=False)
    if action:
        action.write({'code': new_code})
