# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    """Set procedure_for_readings = True and patch action codes."""
    try:
        procedure = env.ref('remotecontrol_scada_mula.remotecontrol_scada_mula'
                            '_procedure_daily_sync')
        procedure.write({'procedure_for_readings': True})
    except Exception:
        pass
    # Patch action: remotecontrol_scada_mula_action_get_devices
    try:
        action = env.ref('remotecontrol_scada_mula.remotecontrol_scada_mula_'
                         'action_get_devices')
        action.write({
            'code': '''
# Build sensors plan from sensor remotecontrol_params
Remote = self.remote_id
Sensor = env['mdm.measurement.device.sensor']
Reading = env['mdm.measurement.device.sensor.reading']
today_str = fields.Date.today()

# Helper function: Calculate hydrological year database name
def get_hydro_year_db(date_str, db_prefix):
    """Calculate database name for hydrological year (Sept 1 - Aug 31)"""
    from datetime import datetime
    dt = datetime.strptime(date_str[:10], '%Y-%m-%d')
    year = dt.year
    month = dt.month
    if month >= 9:
        year1 = year
        year2 = year + 1
    else:
        year1 = year - 1
        year2 = year
    year2_short = str(year2)[2:]
    return '%s_%s_%s' % (db_prefix, year1, year2_short)

def get_hydro_year_start(date_str):
    """Get start of hydrological year for a given date"""
    from datetime import datetime
    dt = datetime.strptime(date_str[:10], '%Y-%m-%d')
    year = dt.year
    month = dt.month
    if month >= 9:
        return '%s-09-01' % year
    else:
        return '%s-09-01' % (year - 1)

# Get connection params
conn_params = json.loads(Remote.connection_params or '{}')
db_prefix = conn_params.get('database_prefix', 'mula')

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
    device_field = sensor_cfg.get('device_field')
    device_id = sensor_cfg.get('device_id')
    date_field = sensor_cfg.get('date_field')
    value_field = sensor_cfg.get('value_field')

    # Validate required parameters
    if not table_name or not device_field or device_id is None or not date_field or not value_field:
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
        # Use start_date from sensor config or start of current hydrological year
        start_cfg = sensor_cfg.get('start_date')
        if start_cfg:
            initial_date = start_cfg[:10]
        else:
            initial_date = get_hydro_year_start(today_str)

    # Calculate which databases are needed based on date range
    databases = []
    start_db = get_hydro_year_db(initial_date, db_prefix)
    end_db = get_hydro_year_db(today_str, db_prefix)

    # For now, collect unique databases needed
    db_set = set([start_db, end_db])
    databases = sorted(list(db_set))

    plan.append({
        'sensor_id': sensor.id,
        'device_id': device.id,
        'table': table_name,
        'device_field': device_field,
        'device_id_value': device_id,
        'date_field': date_field,
        'value_field': value_field,
        'initial_date': initial_date,
        'databases': databases,
    })

bag['sensors_plan'] = plan
bag['plan_count'] = len(plan)
bag['db_prefix'] = db_prefix
''',
        })
    except Exception:
        pass
