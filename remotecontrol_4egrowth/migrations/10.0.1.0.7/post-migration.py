# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    MODULE = 'remotecontrol_4egrowth'

    # ── 1) Update action: Get devices (plan) ──────────────────────────
    #    - parameter / parameter_value are now OPTIONAL
    #    - Only group + key are required
    new_code_get_devices = """
# Action A: build sensors plan (robust JSON parsing)
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
    parameter = (sensor_cfg.get('parameter') or '').strip()
    parameter_value = sensor_cfg.get('parameter_value')
    parameter_group = (sensor_cfg.get('group') or '').strip()
    parameter_key = (sensor_cfg.get('key') or '').strip()
    if parameter_group and parameter_key:
        try:
            device_cfg = (
                json.loads(device.remotecontrol_params or '{}') or
                {}
            )
        except Exception:
            device_cfg = {}
        growth_id = (device_cfg.get('growth_id') or '').strip()
        if growth_id:
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
                start_cfg = (
                    sensor_cfg.get('start_date') or
                    device_cfg.get('start_date')
                )
                if start_cfg:
                    initial_date = start_cfg[:10]
                else:
                    year_str = today_str[:4]
                    initial_date = '%s-01-01' % year_str
            entry = {
                'sensor_id': sensor.id,
                'device_id': device.id,
                'growth_id': growth_id,
                'parameter_group': parameter_group,
                'parameter_key': parameter_key,
                'initial_date': initial_date,
            }
            if parameter and parameter_value not in (None, ''):
                entry['parameter'] = parameter
                entry['parameter_value'] = parameter_value
            plan.append(entry)
bag['sensors_plan'] = plan
"""

    # ── 2) Update action: Get readings ─────────────────────────────────
    #    - parameter / parameter_value only sent when present
    #    - Safe .get() instead of direct dict access (no KeyError)
    new_code_get_readings = """
# Action C: fetch readings by group/key, upsert (generic),
# and attach audit
Remote = self.remote_id
SensorModel = env['mdm.measurement.device.sensor']
plan = bag.get('sensors_plan') or []
token = bag.get('token')
if not token:
    raise Exception("Missing token in bag")
headers = {
    'Authorization': 'Bearer %s' % token,
    'Accept': 'application/json'
}
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
    parameter       = sensor_plan.get('parameter', '')
    parameter_value = sensor_plan.get('parameter_value', '')
    parameter_group = sensor_plan['parameter_group']
    parameter_key   = sensor_plan['parameter_key']
    initial_date    = sensor_plan['initial_date']
    sensor_record = SensorModel.browse(sensor_id)
    base = (
        (base_url or '').rstrip('/') +
        '/api/data_device/%s/all_data/' % growth_id
    )
    params = {'initial_date': initial_date, 'final_date': final_date}
    if parameter and parameter_value not in (None, ''):
        params[parameter] = str(parameter_value)
    try:
        resp = request_retry(
            'GET', base, headers=headers,
            timeout=timeout, params=params
        )
        code = resp.status_code
        full_url = getattr(resp, 'url', base)
        if code < 400:
            payload = resp.json() or {}
            group_data = payload.get(parameter_group)
            if not group_data:
                items.append({
                    'sensor_id': sensor_id,
                    'device_id': device_id,
                    'growth_id': growth_id,
                    'status': 200,
                    'url': full_url,
                    'error': (
                        "Group '%s' not found in response. "
                        "Available groups: %s" %
                        (parameter_group, list(payload.keys()))
                    )
                })
                continue
            key_data = group_data.get(parameter_key)
            if not key_data:
                items.append({
                    'sensor_id': sensor_id,
                    'device_id': device_id,
                    'growth_id': growth_id,
                    'status': 200,
                    'url': full_url,
                    'error': (
                        "Key '%s' not found in group '%s'. "
                        "Available keys: %s" %
                        (parameter_key, parameter_group,
                         list(group_data.keys()))
                    )
                })
                continue
            data_list = key_data.get('data') or []
            window_start = initial_date + window_start_suffix
            window_end   = final_date   + window_end_suffix
            upserts = 0
            errs = 0
            readings_summary = []
            for reading in data_list:
                try:
                    ts_s = reading['ts']
                    raw_value = reading.get('value')
                    valf = (
                        float(raw_value)
                        if raw_value is not None else 0.0
                    )
                    if (ts_s >= window_start) and (ts_s <= window_end):
                        Remote.upsert(
                            'mdm.measurement.device.sensor.reading',
                            {
                                'sensor_id': sensor_record.id,
                                'measurement_time': ts_s
                            },
                            {
                                'value': valf,
                                'remotecontrol_origin_id': Remote.id
                            }
                        )
                        upserts += 1
                        readings_summary.append({
                            'ts': ts_s,
                            'value': valf
                        })
                except Exception as e:
                    errs += 1
                    readings_summary.append({
                        'reading': reading,
                        'error': str(e)
                    })
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
            items.append({
                'sensor_id': sensor_id,
                'device_id': device_id,
                'growth_id': growth_id,
                'status': code,
                'error': (resp.text or '')[:400],
                'url': full_url
            })
    except Exception as e:
        items.append({
            'sensor_id': sensor_id,
            'device_id': device_id,
            'growth_id': growth_id,
            'status': -1,
            'error': str(e)
        })
audit = {
    'executed_at': fields.Datetime.now(),
    'final_date': final_date,
    'total_upserts': total_upserts,
    'total_errors': total_errors,
    'items': items
}
try:
    # Added ensure_asccii to avoid issues with special chars in JSON
    audit_json = json.dumps(
        audit, ensure_ascii=True, indent=2, default=str
    )
    b64 = base64.b64encode(audit_json.encode('utf-8'))
except Exception as json_error:
    # Fallback: create a simplified audit if there are issues
    simple_audit = {
        'executed_at': str(fields.Datetime.now()),
        'total_upserts': total_upserts,
        'total_errors': total_errors,
        'error': str(json_error)
    }
    audit_json = json.dumps(simple_audit, ensure_ascii=True, indent=2)
    b64 = base64.b64encode(audit_json.encode('utf-8'))
fname = 'readings_fetch_%s.json' % (
    fields.Datetime.now()
    .replace(':', '')
    .replace('-', '')
    .replace(' ', '_')
)
att = env['ir.attachment'].create({
    'name': fname,
    'datas_fname': fname,
    'datas': b64,
    'mimetype': 'application/json',
    'res_model': 'remotecontrol',
    'res_id': Remote.id
})
Remote.message_post(
    body=u"[Readings] upserts=%s errors=%s" % (
        total_upserts, total_errors
    ),
    attachment_ids=[att.id]
)
bag['upserts'] = total_upserts
bag['errors'] = total_errors
bag['audit_attachment_id'] = att.id
"""

    # ── 3) Update action: Get devices (plan) ──────────────────────────
    try:
        action_devices = env.ref(
            '%s.remotecontrol_4egrowth_action_get_devices' % MODULE)
        action_devices.write({'code': new_code_get_devices})
    except Exception:
        pass

    # ── 4) Update action: Get readings ─────────────────────────────────
    try:
        action_readings = env.ref(
            '%s.remotecontrol_4egrowth_action_get_readings' % MODULE)
        action_readings.write({'code': new_code_get_readings})
    except Exception:
        pass

    # ── 5) Update remotecontrol_help (changelog + reservoir docs) ──────
    new_help = u"""
<h2>4eGrowth \xb7 Odoo Integration Help</h2>
<p><strong>Official API docs:</strong> <a href="https://panel.4egrowth.com/api-doc" target="_blank" rel="noopener">https://panel.4egrowth.com/api-doc</a></p>

<hr/>

<h3>1) Connection (Remote Control)</h3>
<p>Type: <code>REST</code> \xb7 Base URL: <code>https://panel.4egrowth.com</code></p>
<p><strong>connection_params</strong> (JSON):</p>
<pre>{
  "username": "user@example.com",
  "password": "*******"
}</pre>
<ul>
  <li><em>Get Token</em> calls <code>/api/login/</code> and stores <code>bag["token"]</code> (JWT <code>access</code>).</li>
  <li><em>Get devices (plan)</em> and <em>Get readings</em> send <code>Authorization: Bearer &lt;token&gt;</code>.</li>
</ul>

<h3>2) Default Procedure</h3>
<ol>
  <li><strong>Get Token</strong> \u2192 obtain JWT and store it in the bag.</li>
  <li><strong>Get devices (plan)</strong> \u2192 build <code>bag["sensors_plan"]</code> from device/sensor config.</li>
  <li><strong>Get readings</strong> \u2192 call <code>/api/data_device/{growth_id}/all_data/</code> with filters and upsert readings.</li>
</ol>

<h3>3) Device Configuration</h3>
<p>In each <strong>Device</strong> (<code>mdm.measurement.device</code>) set <em>remotecontrol_params</em>:</p>
<pre>{
  "growth_id": "DEVICE_ID_FROM_4EGROWTH",
  "start_date": "2025-01-01"   // optional fallback if the sensor doesn't define it and no prior readings exist
}</pre>

<h3>4) Sensor Configuration</h3>
<p>In each <strong>Sensor</strong> (<code>mdm.measurement.device.sensor</code>) set <em>remotecontrol_params</em>:</p>
<pre>{
  "parameter": "humedad",           // optional: query filter name (see list below)
  "parameter_value": 30,            // optional: depth or selector (e.g., 30 cm)
  "group": "Humedad suelo",         // REQUIRED: payload group (must match API response exactly)
  "key": "Humedad suelo 30 cm",     // REQUIRED: entry under the group with a "data" array
  "start_date": "2025-01-01"        // optional; else device.start_date; else Jan 1 of current year
}</pre>
<p><strong>Notes</strong></p>
<ul>
  <li><code>parameter</code> and <code>parameter_value</code> are <strong>optional</strong>. When omitted, the API is called with only <code>initial_date</code>/<code>final_date</code> and returns all data groups.</li>
  <li><code>parameter_value</code> may be <em>0</em> and is considered valid.</li>
  <li><code>group</code> and <code>key</code> must match exactly what the endpoint returns in <code>all_data</code>.</li>
</ul>

<h3>5) Time Window</h3>
<ul>
  <li><em>Get devices (plan)</em> computes <code>initial_date</code> per sensor: last stored reading date \u2192 else <code>sensor.start_date</code> \u2192 else <code>device.start_date</code> \u2192 else Jan 1 of current year.</li>
  <li><em>Get readings</em> uses <code>initial_date</code> \u2192 <code>final_date = today</code> and filters points by <code>YYYY-MM-DD HH:MM:SS</code>.</li>
  <li>Timestamps are treated as provided by the API (UTC strings) and stored likewise.</li>
</ul>

<hr/>

<h3>Available query parameters (for <code>/api/data_device/{device_id}/all_data/</code>)</h3>
<p>Use exactly one of these in the sensors <code>parameter</code> field, and set the corresponding <code>parameter_value</code>:</p>
<ul>
  <li><code>humedad</code> (Soil moisture): depth selector. Example values: <code>20</code>, <code>30</code>, <code>40</code>, <code>all</code>, or comma separated (API accepts lists).</li>
  <li><code>temperatura</code> (Soil temperature): depth selector, similar semantics to <em>humedad</em>.</li>
  <li><code>potencial</code> (Matric potential): depth selector, similar semantics.</li>
  <li><code>clima</code> (Weather / generic): variable selector, e.g. <code>eto</code>, <code>temperatura</code>, or <code>all</code>. Also used as the query parameter for reservoir (balsa) devices to retrieve water-height and water-volume data.</li>
</ul>

<h4>Mapping examples (group/key)</h4>
<ul>
  <li>For <strong>Soil moisture</strong> at 30 cm:
    <ul>
      <li><code>parameter</code>: <code>humedad</code></li>
      <li><code>parameter_value</code>: <code>30</code></li>
      <li><code>group</code>: <code>Humedad suelo</code></li>
      <li><code>key</code>: <code>Humedad suelo 30 cm</code></li>
    </ul>
  </li>
  <li>For <strong>Soil temperature</strong> at 20 cm:
    <ul>
      <li><code>parameter</code>: <code>temperatura</code></li>
      <li><code>parameter_value</code>: <code>20</code></li>
      <li><code>group</code>: <code>Temperatura suelo</code></li>
      <li><code>key</code>: <code>Temperatura suelo 20 cm</code></li>
    </ul>
  </li>
  <li>For <strong>Matric potential</strong> at 20 cm:
    <ul>
      <li><code>parameter</code>: <code>potencial</code></li>
      <li><code>parameter_value</code>: <code>20</code></li>
      <li><code>group</code>: <code>Potencial matricial</code></li>
      <li><code>key</code>: <code>Potencial matricial 20 cm</code></li>
    </ul>
  </li>
  <li>For a <strong>Weather</strong> variable:
    <ul>
      <li><code>parameter</code>: <code>clima</code></li>
      <li><code>parameter_value</code>: <code>eto</code> (or <code>all</code>)</li>
      <li><code>group</code>: <code>Clima</code></li>
      <li><code>key</code>: <code>eto</code> (or the exact variable name returned by the API)</li>
    </ul>
  </li>
  <li>For <strong>Water height</strong> (reservoir / balsa):
    <ul>
      <li><code>group</code>: <code>Altura agua</code></li>
      <li><code>key</code>: <code>Altura agua</code></li>
      <li><em>No <code>parameter</code> / <code>parameter_value</code> needed</em></li>
    </ul>
  </li>
  <li>For <strong>Water volume</strong> (reservoir / balsa):
    <ul>
      <li><code>group</code>: <code>Volumen agua</code></li>
      <li><code>key</code>: <code>Volumen agua</code></li>
      <li><em>No <code>parameter</code> / <code>parameter_value</code> needed</em></li>
    </ul>
  </li>
</ul>

<p><strong>Note on reservoir (balsa) devices:</strong> <code>parameter</code> and <code>parameter_value</code> are optional.
When omitted, the API is called with only <code>initial_date</code> / <code>final_date</code> and returns the full payload.
The system then extracts the correct data series using <code>group</code> / <code>key</code>.</p>

<hr/>

<h3>Changelog</h3>
<ul>
  <li><strong>1.0.7</strong> (2026-03-02)
    <ul>
      <li><code>parameter</code> and <code>parameter_value</code> are now <strong>optional</strong> in sensor configuration. When omitted, the API is called without extra filters (only <code>initial_date</code>/<code>final_date</code>), and the system extracts data by <code>group</code>/<code>key</code>.</li>
      <li>Added support for <strong>reservoir (balsa)</strong> devices: <em>Altura agua</em> (water height) and <em>Volumen agua</em> (water volume).</li>
      <li>Replaced direct <code>payload[group][key]</code> access with safe <code>.get()</code> calls to prevent <code>KeyError</code>. Missing groups/keys now produce clear audit warnings showing available keys.</li>
    </ul>
  </li>
  <li><strong>1.0.6</strong> (2026-02)
    <ul>
      <li>Set <code>procedure_for_readings = True</code> on the default sync procedure.</li>
    </ul>
  </li>
  <li><strong>1.0.5</strong> (2026-02)
    <ul>
      <li>Handle null values in <code>reading['value']</code> (defaults to <code>0.0</code>).</li>
      <li>Improved JSON audit serialization (<code>ensure_ascii</code>, fallback on error).</li>
    </ul>
  </li>
  <li><strong>1.0.4</strong> (2026-01)
    <ul>
      <li>Optimized plan builder: single SQL query for last reading per sensor instead of one query per sensor.</li>
    </ul>
  </li>
  <li><strong>1.0.3</strong> (2025-12)
    <ul>
      <li>Audit attachment with full execution details.</li>
    </ul>
  </li>
  <li><strong>1.0.2</strong> (2025-11)
    <ul>
      <li>Added configurable <code>start_date</code> fallback chain (sensor \u2192 device \u2192 Jan 1).</li>
    </ul>
  </li>
  <li><strong>1.0.1</strong> (2025-10)
    <ul>
      <li>Initial release: JWT login, plan builder, readings fetch with upsert.</li>
    </ul>
  </li>
</ul>
"""

    try:
        remote = env.ref(
            '%s.remotecontrol_4egrowth' % MODULE)
        remote.write({'remotecontrol_help': new_help})
    except Exception:
        pass
