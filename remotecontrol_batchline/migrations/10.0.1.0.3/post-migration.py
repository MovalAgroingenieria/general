# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


ACTION_GET_PRESSURE_DEVICES_CODE = u"""# Build pressure sensors plan
Remote = self.remote_id
Sensor = env['mdm.measurement.device.sensor']
Reading = env['mdm.measurement.device.sensor.reading']
today_str = fields.Date.today()
condition = [
    ('remotecontrol_params','!=',False),
    ('device_id.remotecontrol_id', '=', Remote.id)
]
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
    sensor_type = (sensor_cfg.get('sensor_type') or '').strip()
    # Only process pressure sensors
    if sensor_type:
        try:
            device_cfg = json.loads(device.remotecontrol_params or '{}') or {}
        except Exception:
            device_cfg = {}
        hidrante = (device_cfg.get('hidrante') or '').strip()
        electronica = device_cfg.get('electronica')
        canal = device_cfg.get('canal')
        if hidrante and electronica is not None and canal is not None:
            # Retrieve last_reading from map (no query per sensor)
            last_reading_time = last_readings_map.get(sensor.id)
            if last_reading_time:
                try:
                    initial_date = fields.Date.to_string(
                        fields.Datetime.from_string(last_reading_time) +
                        timedelta(days=1))
                except Exception:
                    initial_date = str(last_reading_time)[:10]
            else:
                start_cfg = (sensor_cfg.get('start_date') or device_cfg.get('start_date'))
                if start_cfg:
                    initial_date = start_cfg[:10]
                else:
                    year_str = today_str[:4]
                    initial_date = '%s-01-01' % year_str
            plan.append({
                'sensor_id': sensor.id,
                'device_id': device.id,
                'hidrante': hidrante,
                'electronica': electronica,
                'canal': canal,
                'initial_date': initial_date,
            })
bag['pressure_sensors_plan'] = plan
"""


ACTION_GET_PRESSURE_READINGS_CODE = u"""import pytz
from datetime import datetime
Remote = self.remote_id
SensorModel = env['mdm.measurement.device.sensor']
ReadingModel = env['mdm.measurement.device.sensor.reading']
plan = bag.get('pressure_sensors_plan') or []
token = bag.get('token')
if not token:
    raise Exception("Missing token in bag")
base_api = (base_url or '').rstrip('/') + '/api/presiones/historico'
headers = {'Authorization': 'Bearer %s' % token, 'Accept': 'application/json'}
final_date = fields.Date.today()
total_upserts = 0
total_errors = 0
items = []
for sensor_plan in plan:
    sensor_id = sensor_plan['sensor_id']
    hidrante = sensor_plan['hidrante']
    electronica = sensor_plan['electronica']
    canal = sensor_plan['canal']
    initial_date = sensor_plan['initial_date']
    params = {
        'inicio': initial_date,
        'fin': final_date,
        'hidrante': hidrante,
        'electronica': electronica,
        'canal': canal
    }
    try:
        resp = request_retry('GET', base_api, headers=headers, params=params, timeout=timeout)
        code = resp.status_code
        full_url = getattr(resp, 'url', base_api)
        if code < 400:
            try:
                payload = resp.json() or []
            except Exception as e_json:
                raise
            if isinstance(payload, list):
                readings = payload
            elif isinstance(payload, dict):
                readings = payload.get('data') or []
            else:
                readings = []
            upserts = 0
            errs = 0
            readings_summary = []
            for reading in readings:
                try:
                    ts_s = reading.get('Fecha')
                    valf = float(reading.get('Valor') or 0.0)
                    if ts_s and valf is not None:
                        # Parse timestamp - handle milliseconds if present
                        if '.' in ts_s:
                            ts_parts = ts_s.split('.')
                            ts_base = ts_parts[0]
                            date_time_read = datetime.strptime(ts_base, '%Y-%m-%dT%H:%M:%S')
                        else:
                            date_time_read = datetime.strptime(ts_s, '%Y-%m-%dT%H:%M:%S')
                        date_time_read = pytz.timezone('Europe/Madrid').localize(date_time_read)
                        date_time_read = date_time_read.astimezone(pytz.timezone('UTC'))
                        ts_utc = date_time_read.strftime('%Y-%m-%d %H:%M:%S')
                        Remote.upsert('mdm.measurement.device.sensor.reading', {'sensor_id': sensor_id, 'measurement_time': ts_utc}, {'value': valf, 'remotecontrol_origin_id': Remote.id})
                        upserts += 1
                        readings_summary.append({'ts': ts_utc, 'value': valf})
                except Exception as e:
                    errs += 1
                    readings_summary.append({'error': str(e)})
            total_upserts += upserts
            total_errors += errs
            items.append({'sensor_id': sensor_id, 'device_id': sensor_plan['device_id'], 'status': code, 'url': full_url, 'points_found': len(readings), 'upserts': upserts, 'errors': errs, 'hidrante': hidrante, 'electronica': electronica, 'canal': canal, 'readings': readings_summary})
        else:
            items.append({'sensor_id': sensor_id, 'device_id': sensor_plan['device_id'], 'status': code, 'error': (resp.text or '')[:400], 'url': full_url})
    except Exception as e:
        items.append({'sensor_id': sensor_id, 'device_id': sensor_plan['device_id'], 'status': -1, 'error': str(e)})
audit = {'executed_at': fields.Datetime.now(), 'final_date': final_date, 'total_upserts': total_upserts, 'total_errors': total_errors, 'items': items}
try:
    audit_json = json.dumps(audit, ensure_ascii=True, indent=2, default=str)
    b64 = base64.b64encode(audit_json.encode('utf-8'))
except Exception as json_error:
    simple_audit = {'executed_at': str(fields.Datetime.now()), 'total_upserts': total_upserts, 'total_errors': total_errors, 'error': str(json_error)}
    audit_json = json.dumps(simple_audit, ensure_ascii=True, indent=2)
    b64 = base64.b64encode(audit_json.encode('utf-8'))
fname = 'batchline_pressure_readings_%s.json' % fields.Datetime.now().replace(':', '').replace('-', '').replace(' ', '_')
att = env['ir.attachment'].create({'name': fname, 'datas_fname': fname, 'datas': b64, 'mimetype': 'application/json', 'res_model': 'remotecontrol', 'res_id': Remote.id})
Remote.message_post(body=u"[Batchline pressure readings] upserts=%s errors=%s" % (total_upserts, total_errors), attachment_ids=[att.id])
bag['upserts'] = total_upserts
bag['errors'] = total_errors
bag['audit_attachment_id'] = att.id

"""


ACTION_GET_PRESSURES_LIST_CODE = u"""Remote=self.remote_id
token=bag.get("token")
if not token:
    raise Exception(u"Missing Batchline token in bag")
base_url=(bag.get(u'base_url') or Remote.base_url or u'').rstrip(u'/')+u'/api'
headers={u'Authorization':u'Bearer %s'%token,u'Accept':u'application/json'}

resp=request_retry(u'GET', base_url+u'/presiones', headers=headers, timeout=timeout)
if resp.status_code>=400:
    raise Exception(u"Error fetching pressure devices: %s %s"%(resp.status_code, resp.text))
pressures=resp.json() or []
pressures_list=[]
for p in pressures:
    if not isinstance(p, dict):
        continue
    hidrante=p.get(u'Hidrante') or u'Sin hidrante'
    electronica=p.get(u'Electronica')
    canal=p.get(u'Canal')
    alias=p.get(u'Alias') or u'Sin alias'
    unidad=p.get(u'Unidad') or u''
    fecha=p.get(u'Fecha') or u''
    valor=p.get(u'Valor')
    pressures_list.append({
        u'hidrante': hidrante,
        u'electronica': electronica,
        u'canal': canal,
        u'alias': alias,
        u'unidad': unidad,
        u'fecha': fecha,
        u'valor': valor
    })
summary={
    u'total_pressure_devices': len(pressures_list),
    u'executed_at': fields.Datetime.now()
}
data={
    u'pressures': pressures_list,
    u'summary': summary
}
json_str=json.dumps(data, ensure_ascii=False, indent=2)
encoded=base64.b64encode(json_str.encode(u'utf-8'))
fname=u'batchline_pressures_%s.json'%fields.Datetime.now().replace(u':',u'').replace(u'-',u'').replace(u' ',u'_')
att=env[u'ir.attachment'].create({
    u'name': fname,
    u'datas_fname': fname,
    u'datas': encoded,
    u'mimetype': u'application/json',
    u'res_model': u'remotecontrol',
    u'res_id': Remote.id
})
Remote.message_post(
    body=u'[Batchline] Imported %s pressure devices'%(len(pressures_list)),
    attachment_ids=[att.id]
)
bag.clear()
bag[u'total_pressure_devices']=len(pressures_list)
bag[u'attachment_id']=att.id
bag[u'attachment_name']=fname
"""


UPDATED_HELP_CONTENT = u"""<h2>Batchline · Odoo Integration Help</h2>

<h3>1) Connection (Remote Control)</h3>
<p>Type: <code>REST</code> · Base URL: <code>http://irriweb.crxxx.es:XXXXX</code></p>
<p><strong>connection_params</strong> (JSON):</p>
<pre>{
  "username": "username",
  "password": "password"
}</pre>

<ul>
  <li><em>Get Token</em> calls <code>/token</code> using form data (<code>grant_type=password</code>) and stores <code>bag["token"]</code> (Bearer access token).</li>
  <li><em>Get devices (plan)</em> and <em>Get readings</em> send <code>Authorization: Bearer &lt;token&gt;</code> in headers.</li>
</ul>

<hr>

<h3>2) Procedures</h3>

<h4>2.1 Batchline: Import elements</h4>
<ol>
  <li><strong>Get Token</strong> → obtain access token and store it in <code>bag["token"]</code>.</li>
  <li><strong>Import elements</strong> → call <code>/api/elementos</code> and store the resulting JSON list in an attachment. Each element includes <code>Identificador</code>, <code>Descripción</code>, and a list of <code>Tags</code> with <code>Nombre</code> and <code>Unidad</code>.</li>
</ol>

<h4>2.2 Batchline: Daily Sync</h4>
<ol>
  <li><strong>Get Token</strong> → authenticate and store token in <code>bag["token"]</code>.</li>
  <li><strong>Get devices (plan)</strong> → build <code>bag["sensors_plan"]</code> from Odoo sensors linked to devices with valid <code>remotecontrol_params</code>.</li>
  <li><strong>Get readings</strong> → iterate through plan and call <code>/api/elementos/historico</code> with filters by date, device, and tag to upsert readings into Odoo.</li>
  <li><strong>Get pressure devices (plan)</strong> → build <code>bag["pressure_sensors_plan"]</code> from Odoo sensors with <code>sensor_type</code> defined in their parameters.</li>
  <li><strong>Get pressure readings</strong> → iterate through plan and call <code>/api/presiones/historico</code> with filters by date, hidrante, electronica, and canal to upsert pressure readings into Odoo.</li>
</ol>

<h4>2.3 Batchline: Import pressure devices</h4>
<ol>
  <li><strong>Get Token</strong> → obtain access token and store it in <code>bag["token"]</code>.</li>
  <li><strong>Import pressure devices</strong> → call <code>/api/presiones</code> and store the resulting JSON list in an attachment. Each device includes <code>Hidrante</code>, <code>Electronica</code>, <code>Canal</code>, <code>Alias</code>, <code>Unidad</code>, and current <code>Valor</code>.</li>
</ol>

<hr>

<h3>3) Device Configuration</h3>
<p>Each <strong>Device</strong> (<code>mdm.measurement.device</code>) must define <em>remotecontrol_params</em>:</p>

<h4>For elements-based devices:</h4>
<pre>{
  "device_id": "DEVICE_CODE_FROM_BATCHLINE",
  "start_date": "2025-01-01"   // optional fallback start date
}</pre>

<p><em>device_id</em> corresponds to the "Identificador" returned by the <code>/api/elementos</code> endpoint.</p>

<h4>For pressure devices:</h4>
<pre>{
  "hidrante": "S1-167",
  "electronica": 0,
  "canal": 1,
  "start_date": "2025-01-01"   // optional fallback start date
}</pre>

<p><em>hidrante</em>, <em>electronica</em>, and <em>canal</em> correspond to the values returned by the <code>/api/presiones</code> endpoint.</p>

<hr>

<h3>4) Sensor Configuration</h3>
<p>Each <strong>Sensor</strong> (<code>mdm.measurement.device.sensor</code>) defines <em>remotecontrol_params</em>:</p>

<h4>For elements-based sensors:</h4>
<pre>{
  "tag": "TAG_NAME_IN_BATCHLINE",
  "start_date": "2025-01-01"   // optional; else device.start_date; else Jan 1 of current year
}</pre>

<ul>
  <li><code>tag</code> must match the "Nombre" of a <code>Tag</code> entry returned by the device's <code>/api/elementos</code> response.</li>
  <li>If <code>start_date</code> is missing, it falls back to the device's or the current year.</li>
</ul>

<h4>For pressure sensors:</h4>
<pre>{
  "sensor_type": "H_PRESSURE",
  "start_date": "2025-01-01"   // optional; else device.start_date; else Jan 1 of current year
}</pre>

<ul>
  <li><code>sensor_type</code> must be set to <code>"H_PRESSURE"</code> to indicate this sensor uses the <code>/api/presiones/historico</code> endpoint.</li>
  <li>The <code>hidrante</code>, <code>electronica</code>, and <code>canal</code> values are taken from the parent device configuration.</li>
  <li>If <code>start_date</code> is missing, it falls back to the device's or the current year.</li>
</ul>

<hr>

<h3>5) Time Window and Reading Logic</h3>
<ul>
  <li><em>Get devices (plan)</em> and <em>Get pressure devices (plan)</em> compute <code>initial_date</code> for each sensor:
    last stored reading → else <code>sensor.start_date</code> → else <code>device.start_date</code> → else Jan 1 of current year.
  </li>
  <li><em>Get readings</em> uses <code>inicio</code> = <code>initial_date</code> and <code>fin</code> = today, calling:
    <pre>/api/elementos/historico?inicio=YYYY-MM-DD&amp;fin=YYYY-MM-DD&amp;elemento=DEVICE_ID&amp;tag=TAG_NAME</pre>
  </li>
  <li><em>Get pressure readings</em> uses <code>inicio</code> = <code>initial_date</code> and <code>fin</code> = today, calling:
    <pre>/api/presiones/historico?inicio=YYYY-MM-DD&amp;fin=YYYY-MM-DD&amp;hidrante=HIDRANTE&amp;electronica=N&amp;canal=N</pre>
  </li>
  <li>Timestamps (<code>Fecha</code>) are parsed from ISO format (<code>YYYY-MM-DDTHH:MM:SS</code> or <code>YYYY-MM-DDTHH:MM:SS.mmm</code> with milliseconds), localized to Europe/Madrid, and stored in UTC in Odoo.</li>
</ul>

<hr>

<h3>6) Stored Results</h3>
<ul>
  <li>Each reading (<code>Valor</code>) is upserted into <code>mdm.measurement.device.sensor.reading</code> using <code>sensor_id</code> + <code>measurement_time</code> as unique key.</li>
  <li>An audit JSON file is created and attached to the remote control record after each sync, containing summary, counts, and error details.</li>
  <li>The remote control posts log messages like <em>[Batchline readings] upserts=NN errors=MM</em> and <em>[Batchline pressure readings] upserts=NN errors=MM</em> with attachments.</li>
</ul>

<hr>

<h3>7) Endpoint Summary</h3>
<table border="1" cellspacing="0" cellpadding="5">
  <thead>
    <tr>
      <th>Action</th>
      <th>Endpoint</th>
      <th>Method</th>
      <th>Description</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Get Token</strong></td>
      <td><code>/token</code></td>
      <td>POST (form)</td>
      <td>Authenticate using username/password and obtain Bearer token.</td>
    </tr>
    <tr>
      <td><strong>Import elements</strong></td>
      <td><code>/api/elementos</code></td>
      <td>GET</td>
      <td>Fetch list of available devices and their tags (identifiers, units).</td>
    </tr>
    <tr>
      <td><strong>Import pressure devices</strong></td>
      <td><code>/api/presiones</code></td>
      <td>GET</td>
      <td>Fetch list of available pressure sensors (hidrante, electronica, canal, alias).</td>
    </tr>
    <tr>
      <td><strong>Get hydrants</strong></td>
      <td><code>/api/hidrantes</code></td>
      <td>GET</td>
      <td>Retrieve hydrants information (ID, description, linked devices).</td>
    </tr>
    <tr>
      <td><strong>Get readings</strong></td>
      <td><code>/api/elementos/historico</code></td>
      <td>GET</td>
      <td>Retrieve historical readings filtered by date range, device, and tag.</td>
    </tr>
    <tr>
      <td><strong>Get pressure readings</strong></td>
      <td><code>/api/presiones/historico</code></td>
      <td>GET</td>
      <td>Retrieve historical pressure readings filtered by date range, hidrante, electronica, and canal.</td>
    </tr>
  </tbody>
</table>

<hr>

<h3>8) Typical Data Structures</h3>

<h4>Response from <code>/api/elementos</code>:</h4>
<pre>[
    {
        "Identificador": "EM01",
        "Descripcion": "BUENAVISTA - Filtrado S4",
        "Tags": [
            {
                "Nombre": "H_MINUTOS_OBSERVADOS_DIA",
                "IdItemOPC": 9101066,
                "Unidad": "",
                "Fecha": "2025-10-19T00:00:00",
                "Valor": 1440.00
            },
            {
                "Nombre": "H_TEMPERATURA_EXTERIOR_DIARIA_MAXIMA",
                "IdItemOPC": 9101067,
                "Unidad": "ºC",
                "Fecha": "2025-10-19T16:10:00",
                "Valor": 24.94
            }]
    }
]</pre>

<h4>Response from <code>/api/hidrantes</code>:</h4>
<pre>[
      {
        "Id": "CAB-03_2-01",
        "Nombre": "CAB-03_2",
        "Toma": 1,
        "Fecha": "2025-10-20T08:19:35",
        "Volumen": 0.10,
        "Caudal": 0.00,
        "ModoAuto": false,
        "ValvulaAbierta": false,
        "EstadoValvula": 4,
        "CaudalNominal": 0.00
    }
]</pre>

<h4>Response from <code>/api/elementos/historico</code>:</h4>
<pre>[
  {"Fecha": "2025-10-20T09:00:00", "Valor": 2.54},
  {"Fecha": "2025-10-20T10:00:00", "Valor": 2.58}
]</pre>

<p>Each reading will be inserted or updated in Odoo under the corresponding sensor with <code>value</code> = <code>Valor</code>.</p>

<h4>Response from <code>/api/presiones</code>:</h4>
<pre>[
  {
    "Hidrante": "S1-167",
    "Electronica": 0,
    "Canal": 1,
    "Alias": "Presión entrada filtros",
    "Unidad": "bar",
    "Fecha": "2026-02-04T10:30:00.123",
    "Valor": 2.45
  }
]</pre>

<h4>Response from <code>/api/presiones/historico</code>:</h4>
<pre>[
  {"Fecha": "2026-02-03T00:52:09.967", "Valor": 2.31},
  {"Fecha": "2026-02-03T01:52:09.123", "Valor": 2.28},
  {"Fecha": "2026-02-03T02:52:09.456", "Valor": 2.35}
]</pre>

<p>Each pressure reading will be inserted or updated in Odoo under the corresponding sensor with <code>value</code> = <code>Valor</code>. Timestamps may include milliseconds.</p>

<hr>

<h3>9) Available Tags (Generic and Unique)</h3>
<p>These are all unique tag patterns and names (<code>nombre</code>) available in the Batchline system. Tags with numeric suffixes have been generalized using "X".</p>

<table border="1" cellspacing="0" cellpadding="5">
  <thead>
    <tr>
      <th>Tag Name (generic)</th>
      <th>Unit</th>
      <th>Description (English)</th>
    </tr>
  </thead>
  <tbody>
    <tr><td>H_GENERAL_ENERGIA_SOLAR_TOTAL</td><td>kWh</td><td>Total accumulated solar energy.</td></tr>
    <tr><td>H_GENERAL_ENERGIA_RED_DIARIA</td><td>kWh/dia</td><td>Daily energy consumption from the electrical grid.</td></tr>
    <tr><td>H_GENERAL_ENERGIA_SOLAR_DIARIA</td><td>kWh/dia</td><td>Daily solar energy production.</td></tr>

    <tr><td>H_BOMBAX_ENERGIA_RED_TOTAL</td><td>kWh</td><td>Total grid energy consumed by Pump X.</td></tr>
    <tr><td>H_BOMBAX_ENERGIA_SOLAR_TOTAL</td><td>kWh</td><td>Total solar energy consumed by Pump X.</td></tr>
    <tr><td>H_BOMBAX_ENERGIA_RED_DIARIA</td><td>kWh/dia</td><td>Daily grid energy consumed by Pump X.</td></tr>
    <tr><td>H_BOMBAX_ENERGIA_SOLAR_DIARIA</td><td>kWh/dia</td><td>Daily solar energy consumed by Pump X.</td></tr>

    <tr><td>H_NIVEL</td><td>mca</td><td>Water level in meters of column (hydraulic head).</td></tr>
    <tr><td>H_VOLUMEN</td><td>m3</td><td>Water volume or equivalent hydraulic capacity.</td></tr>

    <tr><td>H_FILTRADO_INF_CICLO_LAVADO</td><td>Desactivado|Activado</td><td>Filter washing cycle state.</td></tr>
    <tr><td>H_FILTRADO_INF_LAVADOS_TOTALES</td><td>Lavados</td><td>Total completed filter wash cycles.</td></tr>
    <tr><td>H_FITLRADO_INF_LAVADOS_PARCIALES</td><td>Lavados</td><td>Partial filter wash cycle count.</td></tr>

    <tr><td>H_PRESION</td><td>bar</td><td>Pressure measurement.</td></tr>
    <tr><td>H_CAUDAL</td><td>l/s</td><td>Instantaneous flow rate (liters per second).</td></tr>

    <tr><td>H_ABIERTA</td><td>ESTADO 0|ESTADO 1</td><td>Valve open state (0=closed, 1=open).</td></tr>
    <tr><td>H_CERRADA</td><td>ESTADO 0|ESTADO 1</td><td>Valve closed state (0=closed, 1=open).</td></tr>

    <tr><td>H_MARCHA</td><td>ESTADO 0|ESTADO 1</td><td>Pump running status (0=stopped, 1=running).</td></tr>
    <tr><td>H_BOYA_ARRANQUE</td><td>Inactiva|Activa</td><td>Start float switch (inactive/active).</td></tr>
    <tr><td>H_BOYA_PARO</td><td>Inactiva|Activa</td><td>Stop float switch (inactive/active).</td></tr>

    <tr><td>H_COBERTURA</td><td>(none)</td><td>Signal coverage or communication quality indicator.</td></tr>
  </tbody>
</table>

<p>All tag names are case-sensitive and must exactly match Batchline API values when defined in <code>sensor.remotecontrol_params</code> in Odoo.</p>

<hr>

<h3>10) Troubleshooting Notes</h3>
<ul>
  <li>If login fails, the action raises <em>"Login failed: [code] [message]"</em>.</li>
  <li>Invalid JSON responses trigger a fallback audit record with basic info.</li>
  <li>API errors (HTTP ≥ 400) are logged per sensor in the audit attachment.</li>
</ul>
"""


def migrate(cr, version):
    """
    Update remotecontrol_help field for Batchline remote control
    to include pressure devices documentation.
    Also create new actions, procedures and steps for pressure handling.
    """
    if not version:
        return

    _logger.info('Starting post-migration for remotecontrol_batchline 10.0.1.0.3')

    env = api.Environment(cr, SUPERUSER_ID, {})

    # Get Batchline remote control record using XML ID
    try:
        remotecontrol = env.ref('remotecontrol_batchline.remotecontrol_batchline')
    except Exception:
        _logger.warning('Batchline remote control not found, skipping migration')
        return

    _logger.info('Found Batchline remote control: %s (id=%s)', remotecontrol.name, remotecontrol.id)

    # Update the remotecontrol_help field
    remotecontrol.write({'remotecontrol_help': UPDATED_HELP_CONTENT})
    _logger.info('Updated remotecontrol_help for Batchline remote control')

    # Get existing procedures
    try:
        procedure_daily_sync = env.ref('remotecontrol_batchline.remotecontrol_batchline_procedure')
    except Exception:
        procedure_daily_sync = None
        _logger.warning('Daily Sync procedure not found')

    # Create or update pressure-related actions
    ActionModel = env['remotecontrol.action']

    # 1. Action: Get pressure devices (plan)
    try:
        action_pressure_devices = env.ref('remotecontrol_batchline.remotecontrol_batchline_action_get_pressure_devices')
    except Exception:
        action_pressure_devices = None

    if not action_pressure_devices:
        _logger.info('Creating action: Get pressure devices (plan)')
        action_pressure_devices = ActionModel.create({
            'name': 'Batchline: Get pressure devices (plan)',
            'remote_id': remotecontrol.id,
            'active': True,
            'rate_limit_seconds': 0.0,
            'max_retries': 1,
            'backoff': 0,
            'readonly': True,
            'code': ACTION_GET_PRESSURE_DEVICES_CODE,
        })
        env['ir.model.data'].create({
            'name': 'remotecontrol_batchline_action_get_pressure_devices',
            'module': 'remotecontrol_batchline',
            'model': 'remotecontrol.action',
            'res_id': action_pressure_devices.id,
        })

    # 2. Action: Get pressure readings
    try:
        action_pressure_readings = env.ref('remotecontrol_batchline.remotecontrol_batchline_action_get_pressure_readings')
    except Exception:
        action_pressure_readings = None

    if not action_pressure_readings:
        _logger.info('Creating action: Get pressure readings')
        action_pressure_readings = ActionModel.create({
            'name': 'Batchline: Get pressure readings',
            'remote_id': remotecontrol.id,
            'active': True,
            'rate_limit_seconds': 0.0,
            'max_retries': 3,
            'backoff': 1.6,
            'readonly': True,
            'code': ACTION_GET_PRESSURE_READINGS_CODE,
        })
        env['ir.model.data'].create({
            'name': 'remotecontrol_batchline_action_get_pressure_readings',
            'module': 'remotecontrol_batchline',
            'model': 'remotecontrol.action',
            'res_id': action_pressure_readings.id,
        })

    # 3. Action: Get pressures list
    try:
        action_pressures_list = env.ref('remotecontrol_batchline.remotecontrol_batchline_action_get_pressures_list')
    except Exception:
        action_pressures_list = None

    if not action_pressures_list:
        _logger.info('Creating action: Get pressures list')
        action_pressures_list = ActionModel.create({
            'name': 'Batchline: Get pressures list',
            'remote_id': remotecontrol.id,
            'active': True,
            'rate_limit_seconds': 0.0,
            'max_retries': 3,
            'backoff': 1.6,
            'readonly': True,
            'code': ACTION_GET_PRESSURES_LIST_CODE,
        })
        env['ir.model.data'].create({
            'name': 'remotecontrol_batchline_action_get_pressures_list',
            'module': 'remotecontrol_batchline',
            'model': 'remotecontrol.action',
            'res_id': action_pressures_list.id,
        })

    # Create procedure for importing pressure devices
    ProcedureModel = env['remotecontrol.procedure']
    try:
        procedure_pressures_import = env.ref('remotecontrol_batchline.remotecontrol_batchline_procedure_pressures_import')
    except Exception:
        procedure_pressures_import = None

    if not procedure_pressures_import:
        _logger.info('Creating procedure: Import pressure devices')
        procedure_pressures_import = ProcedureModel.create({
            'name': 'Batchline: Import pressure devices',
            'remote_id': remotecontrol.id,
            'active': True,
            'schedule_cron': False,
            'readonly': True,
        })
        env['ir.model.data'].create({
            'name': 'remotecontrol_batchline_procedure_pressures_import',
            'module': 'remotecontrol_batchline',
            'model': 'remotecontrol.procedure',
            'res_id': procedure_pressures_import.id,
        })

    # Get token action for procedures
    try:
        action_get_token = env.ref('remotecontrol_batchline.remotecontrol_batchline_action_get_token')
    except Exception:
        action_get_token = None
        _logger.warning('Get Token action not found')

    # Create steps for Daily Sync procedure
    StepModel = env['remotecontrol.step']
    if procedure_daily_sync and action_pressure_devices and action_pressure_readings:
        # Step 40: Get pressure devices (plan)
        try:
            step_40 = env.ref('remotecontrol_batchline.remotecontrol_batchline_step_40_pressure_devices_plan')
        except Exception:
            step_40 = None

        if not step_40:
            _logger.info('Creating step 40: Get pressure devices (plan) for Daily Sync')
            step_40 = StepModel.create({
                'name': 'Get pressure devices (plan)',
                'procedure_id': procedure_daily_sync.id,
                'action_id': action_pressure_devices.id,
                'sequence': 40,
            })
            env['ir.model.data'].create({
                'name': 'remotecontrol_batchline_step_40_pressure_devices_plan',
                'module': 'remotecontrol_batchline',
                'model': 'remotecontrol.step',
                'res_id': step_40.id,
            })

        # Step 50: Get pressure readings
        try:
            step_50 = env.ref('remotecontrol_batchline.remotecontrol_batchline_step_50_pressure_readings')
        except Exception:
            step_50 = None

        if not step_50:
            _logger.info('Creating step 50: Get pressure readings for Daily Sync')
            step_50 = StepModel.create({
                'name': 'Get pressure readings',
                'procedure_id': procedure_daily_sync.id,
                'action_id': action_pressure_readings.id,
                'sequence': 50,
            })
            env['ir.model.data'].create({
                'name': 'remotecontrol_batchline_step_50_pressure_readings',
                'module': 'remotecontrol_batchline',
                'model': 'remotecontrol.step',
                'res_id': step_50.id,
            })

    # Create steps for Import pressure devices procedure
    if procedure_pressures_import and action_get_token and action_pressures_list:
        # Step 10: Get Token
        try:
            step_10_pressures = env.ref('remotecontrol_batchline.remotecontrol_batchline_step_10_token_pressures_import')
        except Exception:
            step_10_pressures = None

        if not step_10_pressures:
            _logger.info('Creating step 10: Get Token for Import pressure devices')
            step_10_pressures = StepModel.create({
                'name': 'Get Token',
                'procedure_id': procedure_pressures_import.id,
                'action_id': action_get_token.id,
                'sequence': 10,
            })
            env['ir.model.data'].create({
                'name': 'remotecontrol_batchline_step_10_token_pressures_import',
                'module': 'remotecontrol_batchline',
                'model': 'remotecontrol.step',
                'res_id': step_10_pressures.id,
            })

        # Step 20: Import pressure devices
        try:
            step_20_pressures = env.ref('remotecontrol_batchline.remotecontrol_batchline_step_20_get_pressures_list')
        except Exception:
            step_20_pressures = None

        if not step_20_pressures:
            _logger.info('Creating step 20: Import pressure devices')
            step_20_pressures = StepModel.create({
                'name': 'Import pressure devices',
                'procedure_id': procedure_pressures_import.id,
                'action_id': action_pressures_list.id,
                'sequence': 20,
            })
            env['ir.model.data'].create({
                'name': 'remotecontrol_batchline_step_20_get_pressures_list',
                'module': 'remotecontrol_batchline',
                'model': 'remotecontrol.step',
                'res_id': step_20_pressures.id,
            })

    _logger.info('Post-migration for remotecontrol_batchline 10.0.1.0.3 completed successfully')
