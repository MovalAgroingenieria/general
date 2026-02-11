# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    new_code_get_devices_list = """
import time
Remote = self.remote_id

cfg = json.loads(Remote.connection_params or '{}') or {}
username = (cfg.get('username') or '').strip()
password = (cfg.get('password') or '').strip()

url = 'https://smart2.inelcom.com:28081/restws/webresources/sesiones'
resp = request_retry('POST', url, json={'usuario': username, 'clave': password}, timeout=180)
if resp.status_code >= 400:
    raise Exception("Login failed: %s %s" % (resp.status_code, resp.text))
id_session = resp.text.strip()
if not id_session:
    raise Exception("Login OK but empty token")

sectors_url = "https://smart2.inelcom.com:28081/restws/webresources/nodos/sectores?sesion=%s" % id_session
resp = request_retry('GET', sectors_url)
if resp.status_code >= 400:
    raise Exception("Sector query failed: %s %s" % (resp.status_code, resp.text))

payload = resp.json() or {}
sectors_list = payload.get("listaSectores", []) or []
devices = []
errors = []

for sector in sectors_list:
    sector_id = sector.get("idSector")
    if not sector_id:
        continue
    url = (
        "https://smart2.inelcom.com:28081/restws/webresources/hidrantes/contadores"
        "?sesion=%s&sector=%s"
    ) % (id_session, sector_id)
    try:
        resp2 = request_retry('GET', url)
        if resp2.status_code >= 400:
            errors.append({'sector': sector_id, 'error': 'HTTP Error %d' % resp2.status_code})
            continue
        data = resp2.json() or {}
        counters_list = data.get("listaContadores", [])
        for counter in counters_list:
            counter_code = counter.get("codContador")
            hydrant_name = counter.get("nombreHidrante") or ""
            counter_number = counter.get("numContador") or ""
            name = "%s - %s" % (hydrant_name, counter_number)
            devices.append({
                'counter_code': counter_code,
                'name': name,
                'hydrant_id': counter.get("idHidrante"),
                'value': counter.get("valor"),
                'sector': sector_id
            })
    except Exception as e:
        errors.append({'sector': sector_id, 'error': str(e)})
    time.sleep(0.5)

locations = []
locations_url = "https://smart2.inelcom.com:28081/restws/webresources/emplazamientos?sesion=%s" % id_session
try:
    resp_locations = request_retry('GET', locations_url)
    if resp_locations.status_code >= 400:
        errors.append({'type': 'locations', 'error': 'HTTP Error %d' % resp_locations.status_code})
    else:
        locations_list = resp_locations.json() or []
        for location in locations_list:
            location_id = location.get("idEmplazamiento")
            location_name = location.get("nombreEmplazamiento")
            sector_name = location.get("nombreSector")
            header_name = location.get("nombreCabezal")

            variables = []
            if location_id:
                variables_url = (
                    "https://smart2.inelcom.com:28081/restws/webresources/emplazamientos/variables"
                    "?sesion=%s&emplazamiento=%s"
                ) % (id_session, location_id)
                try:
                    resp_vars = request_retry('GET', variables_url)
                    if resp_vars.status_code >= 400:
                        errors.append({
                            'type': 'location_variables',
                            'location_id': location_id,
                            'error': 'HTTP Error %d' % resp_vars.status_code
                        })
                    else:
                        variables_list = resp_vars.json() or []
                        for var in variables_list:
                            variables.append({
                                'variable_id': var.get('id'),
                                'variable_name': var.get('nombre')
                            })
                except Exception as e:
                    errors.append({
                        'type': 'location_variables',
                        'location_id': location_id,
                        'error': str(e)
                    })
                time.sleep(0.5)

            locations.append({
                'location_id': location_id,
                'location_name': location_name,
                'sector_name': sector_name,
                'header_name': header_name,
                'sector_code': location.get("codSector"),
                'header_code': location.get("codCabezal"),
                'variables': variables,
                'total_variables': len(variables)
            })
        time.sleep(0.5)
except Exception as e:
    errors.append({'type': 'locations', 'error': str(e)})

result = {
    'executed_at': fields.Datetime.now(),
    'total_devices': len(devices),
    'total_locations': len(locations),
    'total_errors': len(errors),
    'devices': devices,
    'locations': locations,
    'errors': errors,
}

audit_json = json.dumps(result, ensure_ascii=True, indent=2, default=str)
b64 = base64.b64encode(audit_json)
now_str = fields.Datetime.now().replace(':', '').replace('-', '')
fname = 'inelcom_devices_%s.json' % now_str.replace(' ', '_')
att = env['ir.attachment'].create({
    'name': fname,
    'datas_fname': fname,
    'datas': b64,
    'mimetype': 'application/json',
    'res_model': 'remotecontrol',
    'res_id': Remote.id
})

msg = "[Inelcom] Devices: %d, Locations: %d, Errors: %d" % (len(devices), len(locations), len(errors))
Remote.message_post(body=msg, attachment_ids=[att.id])

bag['inelcom_devices'] = devices
bag['inelcom_locations'] = locations
bag['inelcom_devices_errors'] = errors
bag['inelcom_devices_filename'] = fname
"""

    try:
        action_devices_list = env.ref(
            'remotecontrol_inelcom.remotecontrol_inelcom_action_get_devices_list')
        action_devices_list.write({'code': new_code_get_devices_list})
    except Exception:
        pass
