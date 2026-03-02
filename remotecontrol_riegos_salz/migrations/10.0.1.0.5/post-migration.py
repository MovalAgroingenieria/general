# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
"""
Migration 10.0.1.0.5
====================
Applies four fixes to the Riegos Salz remotecontrol action code (noupdate=1
records are never re-written on module update, so we patch them explicitly):

1. API endpoint changed: /wm-rest.php  -->  /apirest
2. MD5 hash case fix: .hexdigest().upper()  -->  .hexdigest()
   (The Riegos Salz API rejects uppercase hashes.)
3. codError check: abort processing for a variable if the API returns a
   non-zero codError, instead of trying to iterate an absent 'historicos' key.
4. procedure_for_readings=True on the Daily Sync procedure so that the
   per-device "Get readings" button can locate it.
"""
from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)

CODE_GET_DEVICES = r"""
from datetime import datetime

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
    sensor_id_value = sensor_cfg.get('id')
    if isinstance(sensor_id_value, int):
        try:
            device_cfg = json.loads(device.remotecontrol_params or '{}') or {}
        except Exception:
            device_cfg = {}
        # Retrieve last_reading from map (no query per sensor)
        last_reading_time = last_readings_map.get(sensor.id)
        if last_reading_time:
            try:
                next_reading = fields.Datetime.from_string(
                    last_reading_time) + timedelta(days=1)
                start_date = next_reading.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                start_date = str(last_reading_time)
        else:
            start_cfg = device_cfg.get('start_date')
            if start_cfg:
                s = start_cfg.strip().replace('/', '-')
                if len(s) == 10:
                    s = s + ' 00:00:00'
                try:
                    dt_cfg = datetime.strptime(s, '%Y-%m-%d %H:%M:%S')
                    start_date = dt_cfg.strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    start_date = s
            else:
                year_str = today_str[:4]
                s2 = '%s-01-01 00:00:00' % year_str
                try:
                    dt_y = datetime.strptime(s2, '%Y-%m-%d %H:%M:%S')
                    start_date = dt_y.strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    start_date = s2
        plan.append({
            'sensor_id': sensor.id,
            'device_id': device.id,
            'sensor_id_value': sensor_id_value,
            'start_date': str(start_date),
        })
bag['sensors_plan'] = plan
"""

CODE_GET_READINGS = r"""
from datetime import datetime
import pytz
import hashlib

Remote = self.remote_id
SensorModel = env['mdm.measurement.device.sensor']
ReadingModel = env['mdm.measurement.device.sensor.reading']
plan = bag.get('sensors_plan') or []
base_url = Remote.base_url
cfg = {}
try:
    cfg = json.loads(Remote.connection_params or '{}') or {}
except Exception:
    cfg = {}
username = (cfg.get('username') or '').strip()
password = (cfg.get('password') or '').strip()
if not username or not password:
    raise Exception("Missing credentials: please configure username/password in connection_params")
password_md5 = hashlib.md5(password.encode('utf-8')).hexdigest()
url = base_url + '/apirest'
headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
total_upserts = 0
total_errors = 0
items = []
tz_madrid = pytz.timezone('Europe/Madrid')
tz_utc = pytz.timezone('UTC')
for sensor_plan in plan:
    sensor_id = sensor_plan['sensor_id']
    device_id = sensor_plan['device_id']
    sensor_id_value = sensor_plan['sensor_id_value']
    start_date = sensor_plan['start_date']
    if len(start_date) == 10:
        fecha_ini = start_date + ' 00:00:00'
    else:
        fecha_ini = start_date
    try:
        s = fecha_ini.strip().replace('/', '-')
        parts = s.split(' ')
        if len(parts) == 1:
            date_part = parts[0]
            time_part = '00:00:00'
        else:
            date_part = parts[0]
            time_part = parts[1]
        ymd = [b.zfill(2) for b in date_part.split('-')]
        hms = [p.zfill(2) for p in time_part.split(':')]
        while len(hms) < 3:
            hms.append('00')
        fecha_ini = "%s-%s-%s %02d:%02d:%02d" % (
            ymd[0], ymd[1], ymd[2],
            int(hms[0]), int(hms[1]), int(hms[2])
        )
    except Exception:
        pass
    payload = {
        'comando': 'consultaHistoricos',
        'correo': username,
        'contrasenya': password_md5,
        'variables': [sensor_id_value],
        'fechaIni': fecha_ini,
    }
    try:
        resp = request_retry('POST', url, headers=headers, json=payload, timeout=Remote.timeout)
        code = resp.status_code
        if code >= 400:
            items.append({
                'sensor_id': sensor_id,
                'status': code,
                'error': (resp.text or '')[:400],
                'url': url
            })
            total_errors += 1
            continue
        data = resp.json() or {}
        cod_error = data.get('codError', -1)
        if cod_error != 0:
            error_msg = data.get('error', '')
            if isinstance(error_msg, list):
                error_msg = '; '.join(error_msg)
            items.append({
                'sensor_id': sensor_id,
                'status': code,
                'error': 'API codError=%s: %s' % (cod_error, error_msg),
                'url': url
            })
            total_errors += 1
            continue
        historicos = data.get('historicos', {}) or {}
        readings = historicos.get(str(sensor_id_value)) or []
        upserts = 0
        errs = 0
        readings_summary = []
        for entry in readings:
            ts_s = entry.get('fecha')
            val_s = entry.get('valor')
            if not ts_s or val_s is None:
                continue
            try:
                valf = float(val_s)
            except Exception:
                continue
            try:
                s2 = unicode(ts_s).strip().replace('/', '-')
                parts2 = s2.split(' ')
                if len(parts2) == 1:
                    date_part2 = parts2[0]
                    time_part2 = '00:00:00'
                else:
                    date_part2 = parts2[0]
                    time_part2 = parts2[1]
                ymd2 = [b.zfill(2) for b in date_part2.split('-')]
                hms2 = [p.zfill(2) for p in time_part2.split(':')]
                while len(hms2) < 3:
                    hms2.append('00')
                ts_norm = "%s-%s-%s %02d:%02d:%02d" % (
                    ymd2[0], ymd2[1], ymd2[2],
                    int(hms2[0]), int(hms2[1]), int(hms2[2])
                )
                dt_ts = datetime.strptime(ts_norm, '%Y-%m-%d %H:%M:%S')
                dt_local = tz_madrid.localize(dt_ts)
                dt_utc = dt_local.astimezone(tz_utc)
                ts_store = dt_utc.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                ts_store = ts_s
            try:
                Remote.upsert(
                    'mdm.measurement.device.sensor.reading',
                    {'sensor_id': sensor_id, 'measurement_time': ts_store},
                    {'value': valf, 'remotecontrol_origin_id': Remote.id}
                )
                upserts += 1
                readings_summary.append({'ts': ts_store, 'value': valf})
            except Exception as e:
                errs += 1
                readings_summary.append({'ts': ts_store, 'value': valf, 'error': str(e)})
        total_upserts += upserts
        total_errors += errs
        items.append({
            'sensor_id': sensor_id,
            'device_id': device_id,
            'sensor_id_value': sensor_id_value,
            'status': 200,
            'url': url,
            'points_found': len(readings),
            'upserts': upserts,
            'errors': errs,
            'readings': readings_summary,
        })
    except Exception as e:
        total_errors += 1
        items.append({'sensor_id': sensor_id, 'status': -1, 'error': str(e)})
audit = {
    'executed_at': fields.Datetime.now(),
    'total_upserts': total_upserts,
    'total_errors': total_errors,
    'items': items,
}
try:
    audit_json = json.dumps(audit, ensure_ascii=True, indent=2, default=str)
    b64 = base64.b64encode(audit_json.encode('utf-8'))
except Exception as json_error:
    simple_audit = {
        'executed_at': str(fields.Datetime.now()),
        'total_upserts': total_upserts,
        'total_errors': total_errors,
        'error': str(json_error),
    }
    audit_json = json.dumps(simple_audit, ensure_ascii=True, indent=2)
    b64 = base64.b64encode(audit_json.encode('utf-8'))
fname = 'readings_riegosalz_%s.json' % fields.Datetime.now().replace(':', '').replace('-', '').replace(' ', '_')
att = env['ir.attachment'].create({
    'name': fname,
    'datas_fname': fname,
    'datas': b64,
    'mimetype': 'application/json',
    'res_model': 'remotecontrol',
    'res_id': Remote.id,
})
Remote.message_post(
    body=u"[RiegosSalz] upserts=%s errors=%s" % (total_upserts, total_errors),
    attachment_ids=[att.id]
)
bag['upserts'] = total_upserts
bag['errors'] = total_errors
bag['audit_attachment_id'] = att.id
"""


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # --- Fix action codes ---
    xmlids = {
        'remotecontrol_riegos_salz_action_get_devices': CODE_GET_DEVICES,
        'remotecontrol_riegos_salz_action_get_readings': CODE_GET_READINGS,
    }
    for xmlid, new_code in xmlids.items():
        try:
            action = env.ref('remotecontrol_riegos_salz.' + xmlid)
            action.write({'code': new_code})
            _logger.info("remotecontrol_riegos_salz 10.0.1.0.5: updated code for %s", xmlid)
        except Exception as e:
            _logger.warning(
                "remotecontrol_riegos_salz 10.0.1.0.5: could not update %s: %s",
                xmlid, e
            )

    # --- Fix procedure_for_readings ---
    try:
        procedure = env.ref(
            'remotecontrol_riegos_salz.remotecontrol_riegos_salz_procedure'
        )
        procedure.write({'procedure_for_readings': True})
        _logger.info(
            "remotecontrol_riegos_salz 10.0.1.0.5: procedure_for_readings set to True"
        )
    except Exception as e:
        _logger.warning(
            "remotecontrol_riegos_salz 10.0.1.0.5: could not set procedure_for_readings: %s", e
        )
