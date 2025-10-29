# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Update action: 4eGrowth: Get readings
    new_code_get_readings = """
# Action C: fetch readings by group/key, upsert (generic), and attach audit
Remote = self.remote_id
SensorModel = env['mdm.measurement.device.sensor']
plan = bag.get('sensors_plan') or []
token = bag.get('token')
if not token:
    raise Exception("Missing token in bag")
headers = {'Authorization': 'Bearer %s' % token, 'Accept': 'application/json'}
final_date = fields.Date.today()
window_start_suffix = ' 00:00:00'
window_end_suffix   = ' 23:59:59'
total_upserts = 0
total_errors = 0
items = []
for sensor_plan in plan:
    sensor_id       = sensor_plan['sensor_id']
    device_id       = sensor_plan['device_id']
    growth_id       = sensor_plan['growth_id']
    parameter       = sensor_plan['parameter']
    parameter_value = sensor_plan['parameter_value']
    parameter_group = sensor_plan['parameter_group']
    parameter_key   = sensor_plan['parameter_key']
    initial_date    = sensor_plan['initial_date']
    sensor_record = SensorModel.browse(sensor_id)
    base = (base_url or '').rstrip('/') + '/api/data_device/%s/all_data/' % growth_id
    params = {'initial_date': initial_date, 'final_date': final_date, parameter: str(parameter_value)}
    try:
        resp = request_retry('GET', base, headers=headers, timeout=timeout, params=params)
        code = resp.status_code
        full_url = getattr(resp, 'url', base)
        if code < 400:
            payload = resp.json() or {}
         if code < 400:
             payload = resp.json() or {}
             data_list = payload.get(parameter_group, {}).get(parameter_key, {}).get('data') or []
             window_start = initial_date + window_start_suffix
            window_start = initial_date + window_start_suffix
            window_end   = final_date   + window_end_suffix
            upserts = 0
            errs = 0
            readings_summary = []
            for reading in data_list:
                try:
                    ts_s = reading['ts']
                    valf = float(reading['value'])
                    if (ts_s >= window_start) and (ts_s <= window_end):
                        Remote.upsert(
                            'mdm.measurement.device.sensor.reading',
                            {'sensor_id': sensor_record.id, 'measurement_time': ts_s},
                            {'value': valf, 'remotecontrol_origin_id': Remote.id}
                        )
                        upserts += 1
                        readings_summary.append({'ts': ts_s, 'value': valf})
                except Exception as e:
                    errs += 1
                    readings_summary.append({'reading': reading, 'error': str(e)})
            total_upserts += upserts
            total_errors  += errs
            items.append({
                'sensor_id': sensor_id,
                'device_id': device_id,
                'growth_id': growth_id,
                'status': 200,
                'url': full_url,
                'points_found': len(data_list),
                'upserts': upserts,
                'errors': errs,
                'group': parameter_group,
                'key': parameter_key,
                'readings': readings_summary,
            })
        else:
            items.append({'sensor_id': sensor_id, 'device_id': device_id, 'growth_id': growth_id, 'status': code, 'error': (resp.text or '')[:400], 'url': full_url})
    except Exception as e:
        items.append({'sensor_id': sensor_id, 'device_id': device_id, 'growth_id': growth_id, 'status': -1, 'error': str(e)})
audit = {'executed_at': fields.Datetime.now(), 'final_date': final_date, 'total_upserts': total_upserts, 'total_errors': total_errors, 'items': items}
try:
    # Added ensure_ascii to avoid issues with special chars in JSON
     audit_json = json.dumps(audit, ensure_ascii=True, indent=2, default=str)
    audit_json = json.dumps(audit, ensure_ascii=True, indent=2, default=str)
    b64 = base64.b64encode(audit_json.encode('utf-8'))
except Exception as json_error:
    # Fallback: create a simplified audit if there are issues
    simple_audit = {'executed_at': str(fields.Datetime.now()), 'total_upserts': total_upserts, 'total_errors': total_errors, 'error': str(json_error)}
    audit_json = json.dumps(simple_audit, ensure_ascii=True, indent=2)
    b64 = base64.b64encode(audit_json.encode('utf-8'))
fname = 'readings_fetch_%s.json' % fields.Datetime.now().replace(':','').replace('-','').replace(' ','_')
att = env['ir.attachment'].create({'name': fname, 'datas_fname': fname, 'datas': b64, 'mimetype': 'application/json', 'res_model': 'remotecontrol', 'res_id': Remote.id})
Remote.message_post(body=u"[Readings] upserts=%s errors=%s" % (total_upserts, total_errors), attachment_ids=[att.id])
bag['upserts'] = total_upserts
bag['errors'] = total_errors
bag['audit_attachment_id'] = att.id
"""
    xml_id_get_readings = 'remotecontrol_4egrowth_action_get_readings'
    try:
        action_get_readings = env.ref(
            'remotecontrol_4egrowth.%s' % xml_id_get_readings)
        action_get_readings.write({'code': new_code_get_readings})
    except Exception:
        pass
