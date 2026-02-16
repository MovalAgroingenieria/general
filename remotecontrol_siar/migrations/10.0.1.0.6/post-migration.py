# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Update action: SiAR: Get readings
    # Fix to handle null values and missing keys in SiAR API responses
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

    # Apply update to action get_readings
    xml_id_get_readings = 'remotecontrol_siar_action_get_readings'
    try:
        action_get_readings = env.ref(
            'remotecontrol_siar.%s' % xml_id_get_readings)
        action_get_readings.write({'code': new_code_get_readings})
    except Exception:
        pass
