# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Get the remotecontrol
    try:
        remotecontrol = env.ref('remotecontrol_siar.remotecontrol_siar')
    except Exception:
        # If remotecontrol doesn't exist, nothing to migrate
        return

    # Update base_url (changed from mapama.gob.es to mapa.gob.es)
    new_base_url = 'https://servicio.mapa.gob.es/siarapi/API/V1'
    if remotecontrol.base_url != new_base_url:
        remotecontrol.write({'base_url': new_base_url})

    # Create new action: SiAR: Get authentication token
    new_code_get_token = """# Action: Get SiAR authentication token
import json

remotecontrol = self.remote_id
base_url = (remotecontrol.base_url or '').rstrip('/')

# Get credentials from connection_params
remotecontrol_cfg = json.loads(remotecontrol.connection_params or '{}') or {}
username = (remotecontrol_cfg.get('username') or '').strip()
password = (remotecontrol_cfg.get('password') or '').strip()

if not username or not password:
    raise Exception('Username and password must be configured in connection_params')

# Step 1: Encrypt username
url_encrypt_user = base_url + '/Autenticacion/cifrarCadena?cadena=' + username
resp_user = request_retry('GET', url_encrypt_user, timeout=timeout)

if resp_user.status_code != 200:
    raise Exception('Failed to encrypt username. Status: %s' % resp_user.status_code)

encrypted_username = resp_user.text.strip().strip('"')

# Step 2: Encrypt password
url_encrypt_pass = base_url + '/Autenticacion/cifrarCadena?cadena=' + password
resp_pass = request_retry('GET', url_encrypt_pass, timeout=timeout)

if resp_pass.status_code != 200:
    raise Exception('Failed to encrypt password. Status: %s' % resp_pass.status_code)

encrypted_password = resp_pass.text.strip().strip('"')

# Step 3: Get token
url_token = (base_url + '/Autenticacion/obtenerToken?Usuario=' +
             encrypted_username + '&Password=' + encrypted_password)
resp_token = request_retry('GET', url_token, timeout=timeout)

if resp_token.status_code != 200:
    raise Exception('Failed to get token. Status: %s, Response: %s' %
                   (resp_token.status_code, resp_token.text[:200]))

token = resp_token.text.strip().strip('"')

if not token or token.lower() == 'null':
    raise Exception('Invalid token received: %s' % resp_token.text[:200])

# Store token in bag for next actions
bag['siar_token'] = token"""

    # Check if action already exists
    action_get_token = env['remotecontrol.action'].search([
        ('remote_id', '=', remotecontrol.id),
        ('name', '=', 'SiAR: Get authentication token')
    ], limit=1)

    if not action_get_token:
        # Create the action
        action_get_token = env['remotecontrol.action'].create({
            'name': 'SiAR: Get authentication token',
            'remote_id': remotecontrol.id,
            'active': True,
            'rate_limit_seconds': 0.0,
            'max_retries': 1,
            'backoff': 0,
            'readonly': True,
            'code': new_code_get_token,
        })

        # Add IrModelData record for the action
        env['ir.model.data'].create({
            'name': 'remotecontrol_siar_action_get_token',
            'module': 'remotecontrol_siar',
            'model': 'remotecontrol.action',
            'res_id': action_get_token.id,
            'noupdate': False,
        })

    # Update action: SiAR: Get readings
    # Changes: Removed all logging, added pytz import, cleaned up code structure
    new_code_get_readings = """# Action B: fetch readings by group/key, upsert (generic), and attach audit
import json
import base64
import pytz
from datetime import datetime, timedelta

remotecontrol = self.remote_id
plan = bag.get('sensors_plan') or []
final_date = (datetime.strptime(fields.Date.today(), "%Y-%m-%d") -
              timedelta(days=1)).strftime("%Y-%m-%d")
total_upserts = 0
total_errors = 0
items = []

for sensor_plan in (plan or []):
    siar_token = sensor_plan['siar_token']
    device_id = sensor_plan['device_id']
    sensor_id = sensor_plan['sensor_id']
    station = sensor_plan['station']
    magnitude = sensor_plan['magnitude']
    initial_date = sensor_plan['initial_date']
    final_date = sensor_plan['final_date']

    url_request = (
        (remotecontrol.base_url or '').rstrip('/') + '/Datos'
        + '/Diarios/ESTACION?Id=%s&FechaInicial=%s&FechaFinal=%s&token=%s'
          % (station, initial_date, final_date, siar_token)
    )

    try:
        resp = request_retry('GET', url_request, timeout=timeout)
        code = resp.status_code

        try:
            payload = resp.json() or {}
        except ValueError:
            # Response is not valid JSON (empty or malformed)
            payload = {}

        mensaje_respuesta = (payload.get('MensajeRespuesta') or '').strip()

        if code < 400:
            # Try both 'datos' (lowercase) and 'Datos' (uppercase) for compatibility
            data_list = payload.get('datos') or payload.get('Datos') or []
            upserts = 0
            errs = 0
            readings_summary = []
            spanish_tz = pytz.timezone('Europe/Madrid')
            utc_tz = pytz.timezone('UTC')

            for reading in data_list:
                # Parse SiAR datetime (Spanish local time) and convert to UTC
                siar_datetime = datetime.strptime(
                    reading['Fecha'], "%Y-%m-%dT%H:%M:%S")
                # 1. Localize naive datetime to Spanish timezone
                spanish_dt = spanish_tz.localize(siar_datetime)
                # 2. Convert to UTC
                utc_dt = spanish_dt.astimezone(utc_tz)
                # 3. Convert to UTC string for database storage
                measurement_time_utc = fields.Datetime.to_string(utc_dt)
                value = float(reading[magnitude])

                try:
                    remotecontrol.upsert(
                        'mdm.measurement.device.sensor.reading',
                        {'sensor_id': sensor_id,
                         'measurement_time': measurement_time_utc},
                        {'remotecontrol_origin_id': remotecontrol.id,
                         'value': value})
                    upserts = upserts + 1
                    readings_summary.append({
                        'measurement_time': measurement_time_utc,
                        'value': value})
                except Exception as e:
                    errs = errs + 1
                    readings_summary.append({
                        'measurement_time': reading['Fecha'],
                        'value': reading[magnitude],
                        'error': str(e)})

            total_upserts = total_upserts + upserts
            total_errors = total_errors + errs
            items.append({
                'sensor_id': sensor_id,
                'device_id': device_id,
                'station': station,
                'magnitude': magnitude,
                'url': url_request,
                'status': 200,
                'points_found': len(data_list),
                'upserts': total_upserts,
                'errors': total_errors,
                'readings': readings_summary})
        else:
            items.append({
                'sensor_id': sensor_id,
                'device_id': device_id,
                'station': station,
                'magnitude': magnitude,
                'status': code,
                'error': mensaje_respuesta,
                'url': url_request})
    except Exception as e:
        items.append({
            'sensor_id': sensor_id,
            'device_id': device_id,
            'station': station,
            'magnitude': magnitude,
            'status': -1,
            'error': str(e),
            'url': url_request})

local_dt = fields.Datetime.to_string(fields.Datetime.context_timestamp(
    self, fields.Datetime.from_string(fields.Datetime.now())))
audit = {
    'executed_at': local_dt,
    'final_date': final_date,
    'total_upserts': total_upserts,
    'total_errors': total_errors,
    'items': items}

try:
    # Added ensure_ascii to avoid issues with special chars in JSON
    audit_json = json.dumps(audit, ensure_ascii=True, indent=2, default=str)
    b64 = base64.b64encode(audit_json.encode('utf-8'))
except Exception as json_error:
    # Fallback: create a simplified audit if there are issues
    simple_audit = {
        'executed_at': local_dt,
        'total_upserts': total_upserts,
        'total_errors': total_errors,
        'error': str(json_error)}
    audit_json = json.dumps(simple_audit, ensure_ascii=True, indent=2)
    b64 = base64.b64encode(audit_json.encode('utf-8'))

fname = 'readings_fetch_%s.json' % local_dt.replace(
    '-', '').replace(' ', '_').replace(':', '')
att = env['ir.attachment'].create({
    'name': fname,
    'datas_fname': fname,
    'datas': b64,
    'mimetype': 'application/json',
    'res_model': 'remotecontrol',
    'res_id': remotecontrol.id})
remotecontrol.message_post(
    body=u"[Readings] upserts=%s errors=%s" % (total_upserts, total_errors),
    attachment_ids=[att.id])

bag['upserts'] = total_upserts
bag['errors'] = total_errors
bag['audit_attachment_id'] = att.id"""

    # Update action: SiAR: Get devices (plan)
    # Changes: Changed api_key to siar_token (from bag), removed api_key validation
    new_code_get_devices = """# Action A: build sensors plan
import json
from datetime import datetime, timedelta
plan = []
siar_token = bag.get('siar_token')
if not siar_token:
    raise Exception('No SiAR token found. Token must be obtained first.')
condition = []
if selected_device_ids:
    condition.append(('id', 'in', selected_device_ids))
else:
    condition.append(('remotecontrol_id', '=', self.remote_id.id))
devices = env['mdm.measurement.device'].search(condition)
if not devices:
    raise Exception('There is no SiAR device.')
yesterday_str = (datetime.strptime(fields.Date.today(), "%Y-%m-%d") -
                 timedelta(days=1)).strftime("%Y-%m-%d")
default_initial_date = '%s-%s-01' % (yesterday_str[:4], yesterday_str[5:7])
default_final_date = yesterday_str
# Optimize: collect all sensor IDs first to avoid N+1 queries
all_sensor_ids = []
for device in (devices or []):
    all_sensor_ids.extend([s.id for s in device.sensor_ids])
# Build map of sensor_id -> most recent reading (single query)
last_readings_map = {}
if all_sensor_ids:
    cr = env.cr
    cr.execute(
        'SELECT DISTINCT ON (sensor_id) sensor_id, measurement_time '
        'FROM mdm_measurement_device_sensor_reading '
        'WHERE sensor_id IN %s AND active = TRUE '
        'ORDER BY sensor_id, measurement_time DESC',
        (tuple(all_sensor_ids),)
    )
    for row in cr.fetchall():
        last_readings_map[row[0]] = row[1]
# Now iterate devices/sensors using the map
for device in (devices or []):
    try:
        device_cfg = json.loads(device.remotecontrol_params or '{}') or {}
    except Exception:
        device_cfg = {}
    station = (device_cfg.get('station') or '').strip()
    if not station:
        continue
    for sensor in (device.sensor_ids or []):
        start_date = (device_cfg.get('start_date') or '').strip()
        if not start_date:
            start_date = default_initial_date
        try:
            sensor_cfg = json.loads(sensor.remotecontrol_params or '{}') or {}
        except Exception:
            sensor_cfg = {}
        magnitude = (sensor_cfg.get('magnitude') or '').strip()
        if not magnitude:
            continue
        sensor_plan = {
            'siar_token': siar_token,
            'device_id': device.id,
            'sensor_id': sensor.id,
            'station': station,
            'magnitude': magnitude
        }
        # Retrieve last_reading from map (no query per sensor)
        last_reading_time = last_readings_map.get(sensor.id)
        if last_reading_time:
            try:
                # last_reading_time comes as string from SQL execute
                start_date = fields.Date.to_string(
                    fields.Datetime.from_string(last_reading_time) +
                    timedelta(days=1))
            except Exception:
                start_date = default_initial_date
        sensor_plan['initial_date'] = start_date
        end_date = default_final_date
        if end_date < start_date:
            end_date = start_date
        sensor_plan['final_date'] = end_date
        plan.append(sensor_plan)
bag['sensors_plan'] = plan"""

    # Apply update to action get_readings
    xml_id_get_readings = 'remotecontrol_siar_action_get_readings'
    try:
        action_get_readings = env.ref(
            'remotecontrol_siar.%s' % xml_id_get_readings)
        action_get_readings.write({'code': new_code_get_readings})
    except Exception:
        pass

    # Apply update to action get_devices
    xml_id_get_devices = 'remotecontrol_siar_action_get_devices'
    try:
        action_get_devices = env.ref(
            'remotecontrol_siar.%s' % xml_id_get_devices)
        action_get_devices.write({'code': new_code_get_devices})
    except Exception:
        pass

    # Get the procedure
    try:
        procedure = env.ref('remotecontrol_siar.remotecontrol_siar_procedure')
    except Exception:
        return

    # Create step for get_token action if it doesn't exist
    step_token = env['remotecontrol.step'].search([
        ('procedure_id', '=', procedure.id),
        ('action_id', '=', action_get_token.id)
    ], limit=1)

    if not step_token:
        step_token = env['remotecontrol.step'].create({
            'name': 'Get authentication token',
            'procedure_id': procedure.id,
            'action_id': action_get_token.id,
            'sequence': 5,
        })

        # Add IrModelData record for the step
        env['ir.model.data'].create({
            'name': 'remotecontrol_siar_step_05_token',
            'module': 'remotecontrol_siar',
            'model': 'remotecontrol.step',
            'res_id': step_token.id,
            'noupdate': False,
        })

    # Update sequences of existing steps to make room
    step_devices = env['remotecontrol.step'].search([
        ('procedure_id', '=', procedure.id),
        ('name', '=', 'Get devices (plan)')
    ], limit=1)
    if step_devices and step_devices.sequence != 10:
        step_devices.write({'sequence': 10})

    step_readings = env['remotecontrol.step'].search([
        ('procedure_id', '=', procedure.id),
        ('name', '=', 'Get readings')
    ], limit=1)
    if step_readings and step_readings.sequence != 20:
        step_readings.write({'sequence': 20})
