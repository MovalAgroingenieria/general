# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID

_CODE_PROVISION_PRESSURE_DEVICES = r"""
import re as _re
Remote = self.remote_id
token = bag.get('token')
if not token:
    raise Exception(u"Missing Batchline token in bag. Run 'Get Token' first.")

api_base = (base_url or '').rstrip('/') + '/api'
headers = {
    u'Authorization': u'Bearer %s' % token,
    u'Accept': u'application/json',
}

resp = request_retry(u'GET', api_base + u'/presiones',
                     headers=headers, timeout=timeout)
if resp.status_code >= 400:
    raise Exception(
        u"Error fetching /api/presiones: %s %s" % (
            resp.status_code, resp.text))
pressures = resp.json() or []
if not isinstance(pressures, list):
    raise Exception(
        u"/api/presiones did not return a list: %r" % pressures)

Device = env['mdm.measurement.device']
Sensor = env['mdm.measurement.device.sensor']

all_devices = Device.search([])
device_by_name = {}
device_by_digits = {}
for dev in all_devices:
    key = (dev.name or '').strip().lower()
    if key:
        device_by_name[key] = dev
    m = _re.search(r'\d+$', key)
    if m:
        device_by_digits[m.group()] = dev

def _find_device(code):
    # Match by Hidrante code (e.g. "ARQ-0036"), NOT by human Alias
    # 1) Exact (case-insensitive)
    exact = device_by_name.get(code.strip().lower())
    if exact:
        return exact, u'exact'
    # 2) Numeric suffix: "ARQ-0036" -> "0036" == "SP-0036" -> "0036"
    m = _re.search(r'\d+$', code.strip())
    if m:
        numeric = device_by_digits.get(m.group())
        if numeric:
            return numeric, u'numeric_suffix'
    return None, None

remotecontrol_rec = env.ref(
    'remotecontrol_batchline.remotecontrol_batchline',
    raise_if_not_found=True)

matched = 0
unmatched = 0
sensors_updated = 0
unmatched_hidrantes = []
details = []

for p in pressures:
    if not isinstance(p, dict):
        continue
    hidrante = (p.get(u'Hidrante') or u'').strip()
    electronica = p.get(u'Electronica')
    canal = p.get(u'Canal')
    alias = (p.get(u'Alias') or u'').strip()
    unidad = (p.get(u'Unidad') or u'').strip()

    if not hidrante or electronica is None or canal is None:
        details.append({u'hidrante': hidrante, u'status': u'skipped_missing_key_fields'})
        continue

    device, match_type = _find_device(hidrante)
    if not device:
        unmatched += 1
        unmatched_hidrantes.append(hidrante)
        details.append({
            u'hidrante': hidrante,
            u'electronica': electronica,
            u'canal': canal,
            u'alias': alias,
            u'status': u'no_match',
        })
        continue

    device_params = {
        u'hidrante': hidrante,
        u'electronica': int(electronica),
        u'canal': int(canal),
    }
    device.write({
        u'name': hidrante,
        u'remotecontrol_id': remotecontrol_rec.id,
        u'remotecontrol_params': json.dumps(device_params, ensure_ascii=False),
    })
    matched += 1

    sensor_params_str = json.dumps(
        {u'sensor_type': u'H_PRESSURE'}, ensure_ascii=False)
    child_sensors = Sensor.search([('device_id', '=', device.id)])
    child_sensors.write({
        u'remotecontrol_id': remotecontrol_rec.id,
        u'remotecontrol_params': sensor_params_str,
    })
    sensors_updated += len(child_sensors)

    details.append({
        u'hidrante': hidrante,
        u'electronica': int(electronica),
        u'canal': int(canal),
        u'alias': alias,
        u'unidad': unidad,
        u'device_id': device.id,
        u'device_name': hidrante,
        u'match_type': match_type,
        u'sensors_updated': len(child_sensors),
        u'status': u'ok',
    })

audit = {
    u'executed_at': fields.Datetime.now(),
    u'total_api_pressures': len(pressures),
    u'matched': matched,
    u'unmatched': unmatched,
    u'sensors_updated': sensors_updated,
    u'unmatched_hidrantes': unmatched_hidrantes,
    u'details': details,
}
b64 = base64.b64encode(
    json.dumps(audit, ensure_ascii=False, indent=2).encode(u'utf-8'))
fname = u'batchline_provision_pressure_%s.json' % (
    fields.Datetime.now()
    .replace(u':', u'').replace(u'-', u'').replace(u' ', u'_'))
att = env[u'ir.attachment'].create({
    u'name': fname,
    u'datas_fname': fname,
    u'datas': b64,
    u'mimetype': u'application/json',
    u'res_model': u'remotecontrol',
    u'res_id': Remote.id,
})
Remote.message_post(
    body=u'[Batchline] Provision pressure devices: '
         u'matched=%s unmatched=%s sensors_updated=%s' % (
             matched, unmatched, sensors_updated),
    attachment_ids=[att.id],
)
bag[u'provision_matched'] = matched
bag[u'provision_unmatched'] = unmatched
bag[u'provision_sensors_updated'] = sensors_updated
bag[u'provision_attachment_id'] = att.id
"""


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    MODULE = 'remotecontrol_batchline'

    xmlid = '%s.remotecontrol_batchline_action_provision_pressure_devices' % MODULE
    action = env.ref(xmlid, raise_if_not_found=False)
    if action:
        action.write({'code': _CODE_PROVISION_PRESSURE_DEVICES})
