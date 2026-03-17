# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    MODULE = 'remotecontrol_4egrowth'

    # ── Fix "Get devices (plan)" action ────────────────────────────────
    #    Remove erroneous +timedelta(days=1) from initial_date calculation.
    #    The old code skipped a full day of data and caused initial_date >
    #    final_date when syncing twice on the same day.  Safe because the
    #    readings action uses upsert, so duplicates are handled gracefully.

    new_code_get_devices = """\
# Action A: build sensors plan (robust JSON parsing)
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
    parameter = (sensor_cfg.get('parameter') or '').strip()
    parameter_value = sensor_cfg.get('parameter_value')
    parameter_group = (sensor_cfg.get('group') or '').strip()
    parameter_key = (sensor_cfg.get('key') or '').strip()
    if parameter_group and parameter_key:
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
                    initial_date = fields.Date.to_string(
                        fields.Datetime.from_string(last_reading_time))
                except Exception:
                    initial_date = str(last_reading_time)[:10]
            else:
                start_cfg = (sensor_cfg.get('start_date') or device_cfg.get('start_date'))
                if start_cfg:
                    initial_date = start_cfg[:10]
                else:
                    year_str = today_str[:4]
                    initial_date = '%s-01-01' % year_str
            entry = {
                'sensor_id': sensor.id,
                'device_id': device.id,
                'growth_id': growth_id,
                'parameter_group': parameter_group,
                'parameter_key': parameter_key,
                'initial_date': initial_date,
            }
            if parameter and parameter_value not in (None, ''):
                entry['parameter'] = parameter
                entry['parameter_value'] = parameter_value
            plan.append(entry)
bag['sensors_plan'] = plan
"""

    xmlid = '%s.remotecontrol_4egrowth_action_get_devices' % MODULE
    action = env.ref(xmlid, raise_if_not_found=False)
    if action:
        action.write({'code': new_code_get_devices})
