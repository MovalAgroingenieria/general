# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


ACTION_GET_READINGS_CODE = """\
headers = bag.get('netilion_headers') or {}
if not headers:
    raise Exception("Missing Netilion credentials in bag. Run 'Validate Credentials' first.")
plans_by_asset = {}
for plan in bag.get('sensors_plan') or []:
    plans_by_asset.setdefault(str(plan['asset_id']), []).append(plan)
items = []
total_upserts = 0
total_errors = 0
for asset_id, asset_plans in plans_by_asset.items():
    try:
        values = []
        page = 1
        while True:
            url = '%s/v1/assets/%s/values?include=unit&page=%s&per_page=100' % ((base_url or '').rstrip('/'), asset_id, page)
            resp = request_retry('GET', url, headers=headers, timeout=timeout)
            if resp.status_code >= 400:
                raise Exception('%s %s' % (resp.status_code, resp.text))
            payload = resp.json() or {}
            records = payload.get('values', [])
            if not isinstance(records, list):
                raise Exception('Unexpected Netilion values response: %s' % payload)
            values.extend(records)
            pagination = payload.get('pagination') or {}
            if page >= int(pagination.get('page_count') or page):
                break
            page += 1
        values_by_key = dict((record.get('key'), record) for record in values if record.get('key'))
        for plan in asset_plans:
            record = values_by_key.get(plan['key']) or {}
            value = record.get('value')
            timestamp = record.get('timestamp') or record.get('time') or record.get('created_at') or ''
            if value in (None, '') or not timestamp:
                raise Exception('Missing value or timestamp for key %s' % plan['key'])
            date_iso = timestamp.replace('T', ' ').replace('Z', '')[:19]
            fields.Datetime.from_string(date_iso)
            with env.cr.savepoint():
                self.remote_id.with_context(
                    disable_test_create_reading=True).upsert(
                    'mdm.measurement.device.sensor.reading',
                    {'sensor_id': plan['sensor_id'], 'measurement_time': date_iso},
                    {'value': float(value), 'device_id': plan['device_id']})
            total_upserts += 1
            items.append({'asset_id': asset_id, 'sensor_id': plan['sensor_id'],
                          'key': plan['key'], 'value': float(value),
                          'date': date_iso, 'unit': record.get('unit')})
    except Exception as error:
        total_errors += len(asset_plans)
        for plan in asset_plans:
            items.append({'asset_id': asset_id, 'sensor_id': plan['sensor_id'],
                          'key': plan['key'], 'error': str(error)})
def to_unicode(value):
    if isinstance(value, str):
        return value.decode('utf-8', 'replace')
    if isinstance(value, list):
        return [to_unicode(item) for item in value]
    if isinstance(value, dict):
        return dict((to_unicode(key), to_unicode(item))
                    for key, item in value.items())
    return value

content = json.dumps(to_unicode({
    'executed_at': fields.Datetime.now(), 'total_upserts': total_upserts,
    'total_errors': total_errors, 'items': items}), ensure_ascii=False, indent=2).encode('utf-8')
fname = 'netilion_readings_%s.json' % fields.Datetime.now().replace(':', '').replace('-', '').replace(' ', '_')
att = env['ir.attachment'].create({
    'name': fname, 'datas_fname': fname, 'datas': base64.b64encode(content),
    'mimetype': 'application/json', 'res_model': 'remotecontrol', 'res_id': self.remote_id.id,
})
self.remote_id.message_post(body=u'[Netilion] upserts=%s errors=%s' % (total_upserts, total_errors), attachment_ids=[att.id])
bag['upserts'] = total_upserts
bag['errors'] = total_errors
"""


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    action = env.ref(
        'remotecontrol_netilion.remotecontrol_netilion_action_get_readings',
        raise_if_not_found=False)
    if action:
        action.write({'code': ACTION_GET_READINGS_CODE})