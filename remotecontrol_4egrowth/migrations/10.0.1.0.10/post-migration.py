# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    MODULE = 'remotecontrol_4egrowth'

    # ── 1) Update action: Get readings ─────────────────────────────────
    #    - Validate resp.json() is a dict before calling .get()
    #    - Log actual API response content in audit when non-dict
    #    - Wrap each batch in try/except + env.cr.commit() for resilience
    new_code_get_readings = """\
# Action C: fetch readings by group/key, upsert (generic), and attach audit.
# - Sensors sharing the same device and parameter type are batched into one
#   API call (parameter_value='all') instead of one call per sensor.
# - Date range is split into 30-day chunks to avoid 502/504 gateway timeouts.
import datetime as _dt

def _date_chunks(start_str, end_str, max_days):
    fmt = '%Y-%m-%d'
    start = _dt.datetime.strptime(start_str, fmt).date()
    end = _dt.datetime.strptime(end_str, fmt).date()
    delta = _dt.timedelta(days=max_days)
    td1 = _dt.timedelta(days=1)
    cur = start
    while cur <= end:
        yield str(cur), str(min(cur + delta - td1, end))
        cur = cur + delta

MAX_DAYS_PER_CHUNK = 30
Remote = self.remote_id
SensorModel = env['mdm.measurement.device.sensor']
plan = bag.get('sensors_plan') or []
token = bag.get('token')
if not token:
    raise Exception("Missing token in bag")
headers = {'Authorization': 'Bearer %s' % token, 'Accept': 'application/json'}
final_date = fields.Date.today()
window_start_suffix = ' 00:00:00'
window_end_suffix = ' 23:59:59'
items = []

# Group sensors by (growth_id, parameter) so they share HTTP calls.
batches = {}
for entry in plan:
    bk = (entry['growth_id'], entry.get('parameter', ''))
    if bk not in batches:
        batches[bk] = []
    batches[bk].append(entry)

for (growth_id, parameter), batch_entries in batches.items():
    base = (base_url or '').rstrip('/') + '/api/data_device/%s/all_data/' % growth_id
    min_initial = min(e['initial_date'] for e in batch_entries)
    sensor_records = {
        e['sensor_id']: SensorModel.browse(e['sensor_id'])
        for e in batch_entries
    }
    # Per-sensor accumulators across all chunks
    sensor_acc = {}
    for entry in batch_entries:
        sensor_acc[entry['sensor_id']] = {
            'upserts': 0,
            'errs': 0,
            'last_url': base,
            'chunk_calls': 0,
            'chunk_http_errors': 0,
            'chunk_exceptions': 0,
            'missing_group': 0,
            'missing_key': 0,
            'chunks': [],
        }

    try:
        for chunk_start, chunk_end in _date_chunks(min_initial, final_date, MAX_DAYS_PER_CHUNK):
            params = {'initial_date': chunk_start, 'final_date': chunk_end}
            if parameter:
                if len(batch_entries) > 1:
                    params[parameter] = 'all'
                else:
                    pv = batch_entries[0].get('parameter_value', '')
                    if pv not in (None, ''):
                        params[parameter] = str(pv)
            params_snapshot = dict(params)

            try:
                resp = request_retry(
                    'GET', base, headers=headers, timeout=timeout, params=params
                )
                code = resp.status_code
                full_url = getattr(resp, 'url', base)

                for entry in batch_entries:
                    sid = entry['sensor_id']
                    sensor_acc[sid]['last_url'] = full_url
                    sensor_acc[sid]['chunk_calls'] += 1

                if code < 400:
                    raw_payload = resp.json()
                    if not isinstance(raw_payload, dict):
                        error_txt = (str(raw_payload) or 'Empty/non-dict response')[:400]
                        for entry in batch_entries:
                            sid = entry['sensor_id']
                            acc = sensor_acc[sid]
                            acc['errs'] += 1
                            acc['chunk_exceptions'] += 1
                            acc['chunks'].append({
                                'chunk_start': chunk_start,
                                'chunk_end': chunk_end,
                                'status': code,
                                'url': full_url,
                                'params': params_snapshot,
                                'error': 'API returned non-dict payload: %s' % error_txt,
                            })
                        continue
                    payload = raw_payload
                    for sp in batch_entries:
                        sid = sp['sensor_id']
                        acc = sensor_acc[sid]
                        sensor_initial = sp['initial_date']
                        window_start = sensor_initial + window_start_suffix
                        window_end = final_date + window_end_suffix
                        chunk_info = {
                            'chunk_start': chunk_start,
                            'chunk_end': chunk_end,
                            'status': code,
                            'url': full_url,
                            'params': params_snapshot,
                            'window_start': window_start,
                            'window_end': window_end,
                            'points_total': 0,
                            'points_in_window': 0,
                            'upserts': 0,
                            'errors': 0,
                        }

                        group_data = payload.get(sp['parameter_group'])
                        if not group_data:
                            acc['missing_group'] += 1
                            acc['errs'] += 1
                            chunk_info['warning'] = (
                                "Group '%s' not found. Available groups: %s" %
                                (sp['parameter_group'], list(payload.keys()))
                            )
                            acc['chunks'].append(chunk_info)
                            continue

                        key_data = group_data.get(sp['parameter_key'])
                        if not key_data:
                            acc['missing_key'] += 1
                            acc['errs'] += 1
                            chunk_info['warning'] = (
                                "Key '%s' not found in group '%s'. Available keys: %s" %
                                (
                                    sp['parameter_key'],
                                    sp['parameter_group'],
                                    list(group_data.keys()),
                                )
                            )
                            acc['chunks'].append(chunk_info)
                            continue

                        data_list = key_data.get('data') or []
                        chunk_info['points_total'] = len(data_list)
                        for reading in data_list:
                            try:
                                ts_s = reading['ts']
                                raw_value = reading.get('value')
                                valf = float(raw_value) if raw_value is not None else 0.0
                                if (ts_s >= window_start) and (ts_s <= window_end):
                                    chunk_info['points_in_window'] += 1
                                    Remote.upsert(
                                        'mdm.measurement.device.sensor.reading',
                                        {
                                            'sensor_id': sensor_records[sid].id,
                                            'measurement_time': ts_s,
                                        },
                                        {
                                            'value': valf,
                                            'remotecontrol_origin_id': Remote.id,
                                        }
                                    )
                                    acc['upserts'] += 1
                                    chunk_info['upserts'] += 1
                            except Exception as e:
                                acc['errs'] += 1
                                chunk_info['errors'] += 1

                        acc['chunks'].append(chunk_info)
                else:
                    error_txt = (resp.text or '')[:400]
                    for entry in batch_entries:
                        sid = entry['sensor_id']
                        acc = sensor_acc[sid]
                        acc['errs'] += 1
                        acc['chunk_http_errors'] += 1
                        acc['chunks'].append({
                            'chunk_start': chunk_start,
                            'chunk_end': chunk_end,
                            'status': code,
                            'url': full_url,
                            'params': params_snapshot,
                            'error': error_txt,
                        })
            except Exception as ex:
                for entry in batch_entries:
                    sid = entry['sensor_id']
                    acc = sensor_acc[sid]
                    acc['errs'] += 1
                    acc['chunk_calls'] += 1
                    acc['chunk_exceptions'] += 1
                    acc['chunks'].append({
                        'chunk_start': chunk_start,
                        'chunk_end': chunk_end,
                        'status': -1,
                        'url': base,
                        'params': params_snapshot,
                        'error': str(ex),
                    })
    except Exception as batch_ex:
        for entry in batch_entries:
            sid = entry['sensor_id']
            acc = sensor_acc[sid]
            acc['errs'] += 1
            acc['chunk_exceptions'] += 1
            acc['chunks'].append({
                'chunk_start': '',
                'chunk_end': '',
                'status': -1,
                'url': base,
                'params': {},
                'error': 'Batch error: %s' % str(batch_ex),
            })

    # Persist upserts for this batch so they survive if a later batch fails
    try:
        env.cr.commit()
    except Exception:
        pass

    # Build one audit item per sensor
    for sp in batch_entries:
        sid = sp['sensor_id']
        acc = sensor_acc[sid]
        if acc['chunk_http_errors'] or acc['chunk_exceptions']:
            sensor_status = 500
        elif acc['missing_group'] or acc['missing_key'] or acc['errs']:
            sensor_status = 207
        else:
            sensor_status = 200

        items.append({
            'sensor_id': sid,
            'device_id': sp['device_id'],
            'growth_id': growth_id,
            'status': sensor_status,
            'url': acc['last_url'],
            'upserts': acc['upserts'],
            'errors': acc['errs'],
            'chunk_calls': acc['chunk_calls'],
            'chunk_http_errors': acc['chunk_http_errors'],
            'chunk_exceptions': acc['chunk_exceptions'],
            'missing_group': acc['missing_group'],
            'missing_key': acc['missing_key'],
            'group': sp['parameter_group'],
            'key': sp['parameter_key'],
            'chunks': acc['chunks'],
        })

total_upserts = sum(i.get('upserts', 0) for i in items)
total_errors = sum(i.get('errors', 0) for i in items)
total_chunk_calls = sum(i.get('chunk_calls', 0) for i in items)
total_chunk_http_errors = sum(i.get('chunk_http_errors', 0) for i in items)
total_chunk_exceptions = sum(i.get('chunk_exceptions', 0) for i in items)
total_missing_group = sum(i.get('missing_group', 0) for i in items)
total_missing_key = sum(i.get('missing_key', 0) for i in items)
audit = {
    'executed_at': fields.Datetime.now(),
    'final_date': final_date,
    'total_upserts': total_upserts,
    'total_errors': total_errors,
    'total_chunk_calls': total_chunk_calls,
    'total_chunk_http_errors': total_chunk_http_errors,
    'total_chunk_exceptions': total_chunk_exceptions,
    'total_missing_group': total_missing_group,
    'total_missing_key': total_missing_key,
    'items': items,
}
try:
    # Added ensure_asccii to avoid issues with special chars in JSON
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

    # ── 2) Update remotecontrol_help (add 1.0.11 changelog entry) ─────
    new_help = u"""\
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
  "start_date": "2026-01-01"   // optional fallback if the sensor doesn't define it and no prior readings exist
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
  <li><strong>1.0.11</strong> (2026-04-17)
    <ul>
      <li>Fixed crash when API returns a non-dict response (e.g. expired JWT token string) with HTTP 200. Now validates <code>resp.json()</code> is a <code>dict</code> before calling <code>.get()</code> and logs the actual API response content in the audit for diagnosis.</li>
      <li>Batch-level <code>cr.commit()</code>: upserts are persisted after each device batch so that a failure in a later batch does not roll back readings already saved.</li>
    </ul>
  </li>
  <li><strong>1.0.9</strong> (2026-04-13)
    <ul>
      <li>Date-range chunking: long date windows are automatically split into 30-day chunks to prevent 502/504 gateway timeouts on the 4eGrowth API when sensors have months of data to fetch.</li>
      <li>Batched API calls: sensors sharing the same device and parameter type (e.g. humedad 30, 60, 90 cm) are fetched in a single HTTP request using <code>parameter=all</code> instead of one request per sensor.</li>
      <li>Enhanced audit JSON: each sensor now includes per-chunk diagnostics (status, URL, params, errors/warnings, and counters) to simplify post-run debugging.</li>
    </ul>
  </li>
  <li><strong>1.0.8</strong> (2026-03-17)
    <ul>
      <li>Fixed <code>initial_date</code> calculation: removed erroneous <code>+1 day</code> offset from last reading date. The old logic skipped a full day of data and caused <code>initial_date &gt; final_date</code> when syncing twice on the same day. Safe because upsert handles duplicates.</li>
    </ul>
  </li>
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
        action_readings = env.ref(
            '%s.remotecontrol_4egrowth_action_get_readings' % MODULE)
        action_readings.write({'code': new_code_get_readings})
    except Exception:
        pass

    try:
        remote = env.ref('%s.remotecontrol_4egrowth' % MODULE)
        remote.write({'remotecontrol_help': new_help})
    except Exception:
        pass
