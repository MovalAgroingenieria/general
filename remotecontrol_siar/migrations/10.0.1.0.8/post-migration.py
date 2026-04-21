# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    MODULE = 'remotecontrol_siar'

    # Fix "Get devices (plan)" action:
    #   5. psycopg2 returns timestamp columns as Python datetime objects, not
    #      strings. fields.Datetime.from_string() fails on them silently,
    #      causing start_date to fall back to the 1st of the month and
    #      re-requesting data that already exists in DB. Use strftime() when
    #      the value already is a datetime object.
    #
    # Fix "Get readings" action:
    #   1. Add time.sleep(60) before first request to let the SiAR rate-limit
    #      window reset after the 3 authentication requests.
    #   2. Add time.sleep(13) between reading requests to stay within 5 req/min.
    #   3. Wrap each upsert in a SAVEPOINT so a PostgreSQL error in upsert does
    #      not abort the whole transaction.
    #   4. Use resp.text[:300] as fallback when MensajeRespuesta is empty,
    #      so error details are visible in the audit JSON.

    new_code = """\
# Action B: fetch readings by group/key, upsert (generic), and attach audit
import json
import base64
import time
import pytz
from datetime import datetime, timedelta

remotecontrol = self.remote_id
plan = bag.get('sensors_plan') or []
final_date = (datetime.strptime(fields.Date.today(), "%Y-%m-%d") -
              timedelta(days=1)).strftime("%Y-%m-%d")
total_upserts = 0
total_errors = 0
items = []

# SiAR rate limit: 5 req/min. Authentication already consumed 3 requests
# (cifrarCadena x2 + obtenerToken), so wait 60 s for the window to reset
# before making any reading request.
if plan:
    time.sleep(60)

for idx, sensor_plan in enumerate(plan or []):
    # Wait 13 s between reading calls to stay within 5 req/min limit
    if idx > 0:
        time.sleep(13)
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

        error_message_siar = (payload.get('MensajeRespuesta') or '').strip()
        if not error_message_siar:
            error_message_siar = resp.text[:300].strip()

        if code < 400:
            # Try both 'datos' (lowercase) and 'Datos' (uppercase) for compatibility
            data_list = payload.get('datos') or payload.get('Datos') or []
            upserts = 0
            errs = 0
            readings_summary = []
            spanish_tz = pytz.timezone('Europe/Madrid')
            utc_tz = pytz.timezone('UTC')

            for reading in data_list:
                # Skip if magnitude key doesn't exist in the reading
                if magnitude not in reading:
                    continue

                # Skip if value is null or empty
                raw_value = reading.get(magnitude)
                if raw_value is None or raw_value == '' or str(raw_value).lower() == 'null':
                    continue

                # Try to convert to float, skip if conversion fails
                try:
                    value = float(raw_value)
                except (ValueError, TypeError):
                    continue

                # Parse SiAR datetime (Spanish local time) and convert to UTC
                try:
                    siar_datetime = datetime.strptime(
                        reading['Fecha'], "%Y-%m-%dT%H:%M:%S")
                    # 1. Localize naive datetime to Spanish timezone
                    spanish_dt = spanish_tz.localize(siar_datetime)
                    # 2. Convert to UTC
                    utc_dt = spanish_dt.astimezone(utc_tz)
                    # 3. Convert to UTC string for database storage
                    measurement_time_utc = fields.Datetime.to_string(utc_dt)
                except Exception:
                    # Skip if date parsing fails
                    continue

                try:
                    env.cr.execute('SAVEPOINT siar_reading_upsert')
                    remotecontrol.upsert(
                        'mdm.measurement.device.sensor.reading',
                        {'sensor_id': sensor_id,
                         'measurement_time': measurement_time_utc},
                        {'remotecontrol_origin_id': remotecontrol.id,
                         'value': value})
                    env.cr.execute('RELEASE SAVEPOINT siar_reading_upsert')
                    upserts = upserts + 1
                    readings_summary.append({
                        'measurement_time': measurement_time_utc,
                        'value': value})
                except Exception as e:
                    env.cr.execute(
                        'ROLLBACK TO SAVEPOINT siar_reading_upsert')
                    errs = errs + 1
                    readings_summary.append({
                        'measurement_time': reading.get('Fecha', 'unknown'),
                        'value': raw_value,
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
                'error': error_message_siar,
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
bag['audit_attachment_id'] = att.id
"""

    xmlid = '%s.remotecontrol_siar_action_get_readings' % MODULE
    action = env.ref(xmlid, raise_if_not_found=False)
    if action:
        action.write({'code': new_code})

    new_code_devices = """\
# Action A: build sensors plan
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
                # psycopg2 returns timestamp columns as Python datetime objects
                if hasattr(last_reading_time, 'strftime'):
                    start_date = last_reading_time.strftime('%Y-%m-%d')
                else:
                    start_date = fields.Date.to_string(
                        fields.Datetime.from_string(last_reading_time))
            except Exception:
                start_date = default_initial_date
        sensor_plan['initial_date'] = start_date
        end_date = default_final_date
        if end_date < start_date:
            end_date = start_date
        sensor_plan['final_date'] = end_date
        plan.append(sensor_plan)
bag['sensors_plan'] = plan
"""

    xmlid_devices = '%s.remotecontrol_siar_action_get_devices' % MODULE
    action_devices = env.ref(xmlid_devices, raise_if_not_found=False)
    if action_devices:
        action_devices.write({'code': new_code_devices})
