# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    new_code_get_devices = """
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
            initial_date = fields.Date.to_string(last_dt + timedelta(days=1))
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

# Plan for location variables
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

    # Only variable_id in the sensor
    variable_id = sensor_cfg.get('variable_id')
    if not variable_id:
        continue

    last_reading_time = last_readings_map.get(sensor.id)
    start_dev = device_cfg.get('start_date')
    start_sensor = sensor_cfg.get('start_date')

    if last_reading_time:
        try:
            last_dt = fields.Datetime.from_string(last_reading_time)
            initial_date = fields.Date.to_string(last_dt + timedelta(days=1))
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

    xml_id_get_devices = 'remotecontrol_inelcom_action_get_devices'
    try:
        action_get_devices = env.ref(
            'remotecontrol_inelcom.%s' % xml_id_get_devices)
        action_get_devices.write({'code': new_code_get_devices})
    except Exception:
        pass

    new_code_location_variables = """
import time
import pytz
from datetime import datetime, timedelta

Remote = self.remote_id
SensorModel = env['mdm.measurement.device.sensor']
Reading = env['mdm.measurement.device.sensor.reading']
today = datetime.now()
plan = bag.get('location_variables_plan') or []
api_url = 'https://smart2.inelcom.com:28081/restws/webresources/emplazamientos/variables/historico'
total_upserts = 0
total_errors = 0
items = []

def get_token():
    cfg = {}
    try:
        cfg = json.loads(Remote.connection_params or '{}')
    except Exception:
        cfg = {}
    username = (cfg.get('username') or '').strip()
    password = (cfg.get('password') or '').strip()
    if not username or not password:
        msg = "Missing inelcom credentials: set username/password"
        raise Exception(msg)
    url = 'https://smart2.inelcom.com:28081/restws/webresources/sesiones'
    resp = request_retry('POST', url, json={
        'usuario': username,
        'clave': password
    })
    if resp.status_code >= 400:
        raise Exception("Login failed: %s %s" % (resp.status_code, resp.text))
    id_session = resp.text.strip()
    if not id_session:
        raise Exception("Login OK but empty token response")
    return id_session

for idx, variable_plan in enumerate(plan, 1):
    sensor_id = variable_plan['sensor_id']
    variable_id = variable_plan['variable_id']
    device_id = variable_plan['device_id']
    initial_date = variable_plan['initial_date']

    dt_initial = datetime.strptime(initial_date, '%Y-%m-%d')
    days = (today.date() - dt_initial.date()).days + 1
    if days < 1:
        days = 1
    date_ddmmyy = dt_initial.strftime('%d/%m/%y')

    try:
        id_session = get_token()
    except Exception as e:
        items.append({
            'sensor_id': sensor_id,
            'error': 'Token error: %s' % str(e)
        })
        total_errors += 1
        continue

    url = "%s?sesion=%s&variable=%s&fecha=%s&dias=%s" % (
        api_url, id_session, variable_id, date_ddmmyy, days
    )

    try:
        resp = request_retry('GET', url, timeout=timeout)
        code = resp.status_code
        full_url = getattr(resp, 'url', url)
        if code < 400:
            payload = resp.json() or {}
            upserts = 0
            errs = 0
            readings_summary = []
            all_readings = []
            readings_list = payload if isinstance(payload, list) else []
            for entry in readings_list:
                try:
                    date_str = entry.get('fecha')
                    time_str = entry.get('hora')
                    value = entry.get('valor')
                    try:
                        dt = datetime.strptime(date_str, '%d/%m/%y')
                        dt = dt.replace(
                            hour=int(time_str[:2]),
                            minute=int(time_str[3:]),
                            second=0
                        )
                        date_time_read = pytz.timezone('Europe/Madrid').localize(dt)
                        date_time_read = date_time_read.astimezone(pytz.timezone('UTC'))
                        ts_str = date_time_read.strftime('%Y-%m-%d %H:%M:%S')
                    except Exception:
                        ts_str = initial_date + ' ' + time_str + ':00'

                    valf = float(value)
                    all_readings.append({'ts': ts_str, 'value': valf})
                    upserts += 1

                    if len(readings_summary) < 5:
                        readings_summary.append({'ts': ts_str, 'value': valf})
                except Exception as e:
                    errs += 1
                    if len(readings_summary) < 5:
                        readings_summary.append({
                            'error': str(e),
                            'raw': entry
                        })

            total_upserts += upserts
            total_errors += errs

            items.append({
                'sensor_id': sensor_id,
                'variable_id': variable_id,
                'device_id': device_id,
                'status': 200,
                'url': full_url,
                'points_found': len(readings_list),
                'upserts': upserts,
                'errors': errs,
                'readings': all_readings,
                'readings_summary': readings_summary
            })
        else:
            items.append({
                'sensor_id': sensor_id,
                'variable_id': variable_id,
                'device_id': device_id,
                'status': code,
                'error': (resp.text or '')[:400],
                'url': full_url
            })
    except Exception as e:
        items.append({
            'sensor_id': sensor_id,
            'variable_id': variable_id,
            'device_id': device_id,
            'status': -1,
            'error': str(e)
        })

    time.sleep(1)

existing_raw = bag.get('raw_readings') or []
for item in items:
    if item.get('status') == 200 and 'readings' in item:
        for reading in item['readings']:
            if 'ts' in reading and 'value' in reading:
                existing_raw.append({
                    'sensor_id': item['sensor_id'],
                    'device_id': item['device_id'],
                    'measurement_time': reading['ts'],
                    'value': reading['value']
                })

bag['raw_readings'] = existing_raw
"""

    try:
        action_location_vars = env.ref(
            'remotecontrol_inelcom.remotecontrol_inelcom_action_get_location_variables_readings')
    except Exception:
        try:
            remote = env.ref('remotecontrol_inelcom.remotecontrol_inelcom')
            action_location_vars = env['remotecontrol.action'].create({
                'name': 'Inelcom: Get Location Variables Data',
                'remote_id': remote.id,
                'active': True,
                'rate_limit_seconds': 0.0,
                'max_retries': 3,
                'backoff': 1.6,
                'readonly': True,
                'code': new_code_location_variables,
            })
            env['ir.model.data'].create({
                'name': 'remotecontrol_inelcom_action_get_location_variables_readings',
                'module': 'remotecontrol_inelcom',
                'model': 'remotecontrol.action',
                'res_id': action_location_vars.id,
                'noupdate': True,
            })
        except Exception:
            pass
    try:
        procedure = env.ref('remotecontrol_inelcom.remotecontrol_inelcom_procedure')
        existing_step = env['remotecontrol.step'].search([
            ('procedure_id', '=', procedure.id),
            ('sequence', '=', 25)
        ], limit=1)

        if not existing_step:
            try:
                action_location_vars = env.ref(
                    'remotecontrol_inelcom.remotecontrol_inelcom_action_get_location_variables_readings')
                step = env['remotecontrol.step'].create({
                    'name': 'Get Location Variables Data',
                    'procedure_id': procedure.id,
                    'action_id': action_location_vars.id,
                    'sequence': 25,
                })
                env['ir.model.data'].create({
                    'name': 'remotecontrol_inelcom_step_25_location_variables_readings',
                    'module': 'remotecontrol_inelcom',
                    'model': 'remotecontrol.step',
                    'res_id': step.id,
                    'noupdate': True,
                })
            except Exception:
                pass
    except Exception:
        pass
