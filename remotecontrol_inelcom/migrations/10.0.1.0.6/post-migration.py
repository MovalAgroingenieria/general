# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    MODULE = 'remotecontrol_inelcom'

    # Update "Get Devices Plan" action: add analog_inputs_plan block
    # so sensors with (hidrante + entrada) params are planned alongside
    # counters and location variables.

    new_get_devices_code = """\
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
            initial_date = fields.Date.to_string(last_dt)
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

    variable_id = sensor_cfg.get('variable_id')
    if not variable_id:
        continue

    last_reading_time = last_readings_map.get(sensor.id)
    start_dev = device_cfg.get('start_date')
    start_sensor = sensor_cfg.get('start_date')

    if last_reading_time:
        try:
            last_dt = fields.Datetime.from_string(last_reading_time)
            initial_date = fields.Date.to_string(last_dt)
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

analog_inputs_plan = []
for sensor in Sensor.search([
    ('remotecontrol_params', '!=', False),
    ('device_id.remotecontrol_id', '=', Remote.id)
] + ([('device_id', 'in', selected_device_ids)] if selected_device_ids else [])):
    device = sensor.device_id
    try:
        sensor_cfg = json.loads(sensor.remotecontrol_params or '{}') or {}
    except Exception:
        sensor_cfg = {}
    try:
        device_cfg = json.loads(device.remotecontrol_params or '{}') or {}
    except Exception:
        device_cfg = {}
    hidrante = device_cfg.get('hidrante')
    entrada = sensor_cfg.get('entrada')
    if not (hidrante and entrada is not None):
        continue
    last_reading_time = last_readings_map.get(sensor.id)
    start_dev = device_cfg.get('start_date')
    start_sensor = sensor_cfg.get('start_date')
    if last_reading_time:
        try:
            last_dt = fields.Datetime.from_string(last_reading_time)
            initial_date = fields.Date.to_string(last_dt)
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
    analog_inputs_plan.append({
        'sensor_id': sensor.id,
        'device_id': device.id,
        'hidrante': hidrante,
        'entrada': entrada,
        'initial_date': initial_date,
    })
bag['analog_inputs_plan'] = analog_inputs_plan
"""

    # Update the existing Get Devices Plan action
    xmlid = '%s.remotecontrol_inelcom_action_get_devices' % MODULE
    action = env.ref(xmlid, raise_if_not_found=False)
    if action:
        action.write({'code': new_get_devices_code})

    # Create the new Get Analog Inputs Data action if it does not exist yet
    new_analog_action_code = """\
import time
import pytz
from datetime import datetime

Remote = self.remote_id
today = datetime.now()
plan = bag.get('analog_inputs_plan') or []
api_url = Remote.base_url.rstrip('/').replace(
    '/restws', '') + '/isrlrestws/resources/hidrantes/histanalogicas'
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
        raise Exception("Missing inelcom credentials: set username/password")
    login_url = Remote.base_url.rstrip('/') + '/webresources/sesiones'
    resp = request_retry('POST', login_url, json={
        'usuario': username,
        'clave': password
    })
    if resp.status_code >= 400:
        raise Exception("Login failed: %s %s" % (resp.status_code, resp.text))
    id_session = resp.text.strip()
    if not id_session:
        raise Exception("Login OK but empty token response")
    return id_session


for idx, entry_plan in enumerate(plan, 1):
    sensor_id = entry_plan['sensor_id']
    device_id = entry_plan['device_id']
    hidrante = entry_plan['hidrante']
    entrada = entry_plan['entrada']
    initial_date = entry_plan['initial_date']

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
            'error': 'Token error: %s' % str(e),
        })
        total_errors += 1
        continue

    url = "%s?sesion=%s&hidrante=%s&entrada=%s&fecha=%s&dias=%s" % (
        api_url, id_session, hidrante, entrada, date_ddmmyy, days
    )

    try:
        resp = request_retry('GET', url, timeout=timeout)
        code = resp.status_code
        full_url = getattr(resp, 'url', url)
        if code < 400:
            payload = resp.json() or {}
            upserts = 0
            errs = 0
            all_readings = []
            readings_summary = []
            lista = payload.get('lista') or (
                payload if isinstance(payload, list) else []
            )
            for rec in lista:
                try:
                    date_str = rec.get('fecha')
                    time_str = rec.get('hora')
                    value = rec.get('valor')
                    try:
                        dt = datetime.strptime(date_str, '%d/%m/%y')
                        dt = dt.replace(
                            hour=int(time_str[:2]),
                            minute=int(time_str[3:]),
                            second=0
                        )
                        date_time_read = pytz.timezone(
                            'Europe/Madrid').localize(dt)
                        date_time_read = date_time_read.astimezone(
                            pytz.timezone('UTC'))
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
                        readings_summary.append({'error': str(e), 'raw': rec})
            total_upserts += upserts
            total_errors += errs
            items.append({
                'sensor_id': sensor_id,
                'device_id': device_id,
                'hidrante': hidrante,
                'entrada': entrada,
                'status': 200,
                'url': full_url,
                'points_found': len(lista),
                'upserts': upserts,
                'errors': errs,
                'readings': all_readings,
                'readings_summary': readings_summary,
            })
        else:
            items.append({
                'sensor_id': sensor_id,
                'device_id': device_id,
                'hidrante': hidrante,
                'entrada': entrada,
                'status': code,
                'error': (resp.text or '')[:400],
                'url': full_url,
            })
    except Exception as e:
        items.append({
            'sensor_id': sensor_id,
            'device_id': device_id,
            'hidrante': hidrante,
            'entrada': entrada,
            'status': -1,
            'error': str(e),
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
                    'value': reading['value'],
                })
bag['raw_readings'] = existing_raw
"""

    RemoteAction = env['remotecontrol.action']
    RemoteStep = env['remotecontrol.step']
    remote = env.ref(
        '%s.remotecontrol_inelcom' % MODULE, raise_if_not_found=False)
    procedure = env.ref(
        '%s.remotecontrol_inelcom_procedure' % MODULE,
        raise_if_not_found=False)

    existing_action = env.ref(
        '%s.remotecontrol_inelcom_action_get_analog_inputs_readings' % MODULE,
        raise_if_not_found=False)

    if not existing_action and remote:
        new_action = RemoteAction.create({
            'name': 'Inelcom: Get Analog Inputs Data',
            'remote_id': remote.id,
            'active': True,
            'rate_limit_seconds': 0.0,
            'max_retries': 3,
            'backoff': 1.6,
            'readonly': True,
            'code': new_analog_action_code,
        })
        env['ir.model.data'].create({
            'name': 'remotecontrol_inelcom_action_get_analog_inputs_readings',
            'module': MODULE,
            'model': 'remotecontrol.action',
            'res_id': new_action.id,
            'noupdate': True,
        })
        if procedure:
            RemoteStep.create({
                'name': 'Get Analog Inputs Data',
                'procedure_id': procedure.id,
                'action_id': new_action.id,
                'sequence': 27,
            })
    elif existing_action:
        existing_action.write({'code': new_analog_action_code})
