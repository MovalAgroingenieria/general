# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    """Set procedure_for_readings = True and patch action codes."""
    try:
        procedure = env.ref('remotecontrol_scada_abaran.remotecontrol_scada'
                            '_abaran_procedure_daily_sync')
        procedure.write({'procedure_for_readings': True})
    except Exception:
        pass
    # Patch action: remotecontrol_scada_abaran_action_get_devices
    try:
        action = env.ref('remotecontrol_scada_abaran.remotecontrol_scada_'
                         'abaran_action_get_devices')
        action.write({
            'code': '''
# Build sensors plan from sensor remotecontrol_params
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
    # Get configuration from sensor
    table_name = sensor_cfg.get('table')
    remota = sensor_cfg.get('remota')
    identificador = sensor_cfg.get('identificador')
    tipo_informacion = sensor_cfg.get('tipo_informacion')
    # Validate required parameters
    if not table_name or remota is None or identificador is None or tipo_informacion is None:
        continue
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
        'table': table_name,
        'remota': remota,
        'identificador': identificador,
        'tipo_informacion': tipo_informacion,
        'initial_date': initial_date,
    })
bag['sensors_plan'] = plan
bag['plan_count'] = len(plan)
''',
        })
    except Exception:
        pass
