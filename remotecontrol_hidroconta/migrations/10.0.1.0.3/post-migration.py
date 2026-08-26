# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return

    action_xmlid = ('remotecontrol_hidroconta.'
                    'remotecontrol_hidroconta_action_get_readings')
    env = api.Environment(cr, SUPERUSER_ID, {})
    action = env.ref(action_xmlid, raise_if_not_found=False)
    if not action:
        return

    action_code = """\
if 'jsessionid' not in bag:
    raise Exception('Please run "Hidroconta: Login" action first')
if 'sensor_plan' not in bag:
    raise Exception('Please run "Hidroconta: Build Sensor Plan" action first')
Remote = self.remote_id
jsessionid = bag['jsessionid']
sensor_plan = bag['sensor_plan']
cookies = {'JSESSIONID': jsessionid}
url = (base_url or '').rstrip('/') + '/Demeter2/v2/history/data'
Reading = env['mdm.measurement.device.sensor.reading']
Sensor = env['mdm.measurement.device.sensor']
total_readings = 0
total_sensors = len(sensor_plan)
total_errors = 0
items = []
now_str = fields.Datetime.now()
for plan_item in sensor_plan:
    odoo_sensor_id = plan_item['odoo_sensor_id']
    element_id = plan_item['element_id']
    subtype = plan_item['subtype']
    subcode = plan_item['subcode']
    start_date_str = plan_item.get('start_date', '2025-01-01')
    conversion_factor = plan_item.get('conversion_factor', 1.0)
    try:
        conversion_factor = float(conversion_factor)
    except Exception:
        conversion_factor = 1.0
    sensor = Sensor.browse(odoo_sensor_id)
    if not sensor.exists():
        continue
    last_reading = Reading.search([
        ('sensor_id', '=', odoo_sensor_id)
    ], order='measurement_time desc', limit=1)
    if last_reading:
        start_date_time = str(last_reading.measurement_time)
    else:
        start_date_time = start_date_str + ' 00:00:00'
    start_parts = start_date_time.split(' ')
    start_date_parts = start_parts[0].split('-')
    from_formatted = '%s/%s/%s %s' % (
        start_date_parts[2],
        start_date_parts[1],
        start_date_parts[0],
        start_parts[1],
    )
    now_parts = now_str.split(' ')
    now_date_parts = now_parts[0].split('-')
    until_formatted = '%s/%s/%s %s' % (
        now_date_parts[2],
        now_date_parts[1],
        now_date_parts[0],
        now_parts[1],
    )
    payload = {
        'from': from_formatted,
        'until': until_formatted,
        'elementIds': [element_id],
        'subtype': subtype,
        'subcode': [subcode],
    }
    sensor_upserts = 0
    sensor_errors = 0
    readings_summary = []
    try:
        resp = request_retry(
            'POST',
            url,
            json=payload,
            cookies=cookies,
            timeout=timeout,
        )
        if resp.status_code >= 400:
            sensor_errors += 1
            continue
        readings = resp.json() or []
        for reading in readings:
            historic_date = reading.get('historicDate')
            value = reading.get('value')
            if not historic_date or value is None:
                continue
            try:
                converted_value = float(value) * conversion_factor
            except Exception as e:
                sensor_errors += 1
                total_errors += 1
                if len(readings_summary) < 5:
                    readings_summary.append({
                        'error': str(e),
                        'ts': historic_date,
                        'value': value,
                    })
                continue
            date_time_parts = historic_date.split(' ')
            if len(date_time_parts) != 2:
                continue
            date_part = date_time_parts[0]
            time_part = date_time_parts[1]
            date_components = date_part.split('/')
            if len(date_components) != 3:
                continue
            ts_formatted = '%s-%s-%s %s' % (
                date_components[2],
                date_components[1],
                date_components[0],
                time_part,
            )
            date_time_read = fields.Datetime.from_string(ts_formatted)
            date_time_read = pytz.timezone('Europe/Madrid').localize(
                date_time_read)
            date_time_read = date_time_read.astimezone(
                pytz.timezone('UTC'))
            ts_formatted = date_time_read.strftime('%Y-%m-%d %H:%M:%S')
            try:
                Remote.upsert(
                    'mdm.measurement.device.sensor.reading',
                    {
                        'sensor_id': odoo_sensor_id,
                        'measurement_time': ts_formatted,
                    },
                    {'value': converted_value},
                )
                sensor_upserts += 1
                total_readings += 1
                if len(readings_summary) < 5:
                    readings_summary.append({
                        'ts': ts_formatted,
                        'value': converted_value,
                        'raw_value': value,
                    })
            except Exception as e:
                sensor_errors += 1
                total_errors += 1
                if len(readings_summary) < 5:
                    readings_summary.append({
                        'error': str(e),
                        'ts': historic_date,
                        'value': value,
                    })
        items.append({
            'sensor_id': odoo_sensor_id,
            'sensor_name': sensor.name,
            'element_id': element_id,
            'conversion_factor': conversion_factor,
            'upserts': sensor_upserts,
            'errors': sensor_errors,
            'sample_readings': readings_summary,
        })
    except Exception as e:
        total_errors += 1
        items.append({
            'sensor_id': odoo_sensor_id,
            'sensor_name': sensor.name,
            'element_id': element_id,
            'error': str(e),
        })
audit = {
    'executed_at': fields.Datetime.now(),
    'total_sensors': total_sensors,
    'total_upserts': total_readings,
    'total_errors': total_errors,
    'items': items,
}
b64 = base64.b64encode(
    json.dumps(audit, indent=2, ensure_ascii=False).encode('utf-8'))
fname = 'hidroconta_readings_%s.json' % (
    fields.Datetime.now().replace(':', '').replace('-', '').replace(' ', '_'))
att = env['ir.attachment'].create({
    'name': fname,
    'datas_fname': fname,
    'datas': b64,
    'mimetype': 'application/json',
    'res_model': 'remotecontrol',
    'res_id': Remote.id,
})
bag['attachment_id'] = att.id
bag['attachment_name'] = fname
result = ('Processed %d sensors, %d readings loaded, %d errors. '
          'File saved: %s') % (
    total_sensors,
    total_readings,
    total_errors,
    fname,
)
"""

    action.write({'code': action_code})
