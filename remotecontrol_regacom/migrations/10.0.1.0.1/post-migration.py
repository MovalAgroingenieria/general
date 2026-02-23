# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    """Set procedure_for_readings = True and patch action codes."""
    try:
        procedure = env.ref('remotecontrol_regacom.remotecontrol_'
                            'regacom_procedure_daily_sync')
        procedure.write({'procedure_for_readings': True})
    except Exception:
        pass
    # Patch action: remotecontrol_regacom_action_get_devices
    try:
        action = env.ref('remotecontrol_regacom.remotecontrol_regacom_'
                         'action_get_devices')
        action.write({
            'code': '''
# Build sensors plan from device/sensor remotecontrol_params
Remote = self.remote_id
Sensor = env['mdm.measurement.device.sensor']
Reading = env['mdm.measurement.device.sensor.reading']
today_str = fields.Date.today()
# Get all sensors with remotecontrol_params configured for THIS remote control
condition = [
    ('remotecontrol_params', '!=', False),
    ('device_id.remotecontrol_id', '=', Remote.id),
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
plan = []
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
    # Get table configuration from sensor
    table_name = sensor_cfg.get('table')
    value_field = sensor_cfg.get('value_field')
    time_field = sensor_cfg.get('time_field')
    pk_fields = sensor_cfg.get('pk_fields', [])
    pk_values = sensor_cfg.get('pk_values', [])
    # Validate required parameters
    if table_name and value_field and time_field and pk_fields and len(pk_fields) == len(pk_values):
        # Determine initial date for this sensor
        last_reading_time = last_readings_map.get(sensor.id)
        if last_reading_time:
            try:
                initial_date = fields.Date.to_string(
                    fields.Datetime.from_string(last_reading_time) +
                    timedelta(days=1))
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
        # Build final pk_values replacing nulls with device values
        # Use pk_fields names as keys to get values from device_cfg
        final_pk_values = []
        all_fields_ok = True
        for i, val in enumerate(pk_values):
            if val is None:
                # Get value from device config using the field name
                field_name = pk_fields[i] if i < len(pk_fields) else None
                if field_name:
                    device_val = device_cfg.get(field_name)
                    if device_val is not None:
                        final_pk_values.append(device_val)
                    else:
                        all_fields_ok = False
                        break
                else:
                    all_fields_ok = False
                    break
            else:
                final_pk_values.append(val)

        if not all_fields_ok:
            continue

        plan.append({
            'sensor_id': sensor.id,
            'device_id': device.id,
            'table': table_name,
            'value_field': value_field,
            'time_field': time_field,
            'pk_fields': pk_fields,
            'pk_values': final_pk_values,
            'initial_date': initial_date,
        })
bag['sensors_plan'] = plan
bag['plan_count'] = len(plan)
''',
        })
    except Exception:
        pass
