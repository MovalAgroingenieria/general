# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    MODULE = 'remotecontrol_ikostech'

    # ── 1) Update action: Build devices plan ──────────────────────────
    #    - Extract serial from device params and field from sensor params
    #    - Use latest existing reading date as incremental start date
    new_code_build_plan = """\
# Action A: build sensors plan
# For each sensor with remotecontrol_params, extract serial + field name
Remote = self.remote_id
Sensor = env['mdm.measurement.device.sensor']
today_str = fields.Date.today()

condition = [
    ('remotecontrol_params', '!=', False),
    ('device_id.remotecontrol_id', '=', Remote.id)
]
if selected_device_ids:
    condition.append(('device_id', 'in', selected_device_ids))

sensors = Sensor.search(condition)

# Optimize: build map of last reading per sensor (single query)
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

plan = []
for sensor in sensors:
    device = sensor.device_id
    try:
        device_cfg = json.loads(device.remotecontrol_params or '{}') or {}
    except Exception:
        device_cfg = {}
    try:
        sensor_cfg = json.loads(sensor.remotecontrol_params or '{}') or {}
    except Exception:
        sensor_cfg = {}

    serial = (device_cfg.get('serial') or '').strip()
    field = (sensor_cfg.get('field') or '').strip()

    if serial and field:
        # Determine initial date: last_reading → device.start_date → Jan 1
        last_reading_time = last_readings_map.get(sensor.id)
        if last_reading_time:
            try:
                initial_date = fields.Date.to_string(
                    fields.Datetime.from_string(last_reading_time))
            except Exception:
                initial_date = str(last_reading_time)[:10]
        else:
            start_date = device_cfg.get('start_date')
            if start_date:
                initial_date = start_date[:10]
            else:
                year_str = today_str[:4]
                initial_date = '%s-01-01' % year_str

        plan.append({
            'sensor_id': sensor.id,
            'device_id': device.id,
            'serial': serial,
            'field': field,
            'initial_date': initial_date,
        })

bag['sensors_plan'] = plan
bag['total_sensors'] = len(plan)
result = 'Built plan for %d IkosTech sensors' % len(plan)
"""

    # ── 2) Update action: Fetch readings ──────────────────────────────
    #    - Group sensors by serial so one API call feeds several sensors
    #    - Retry 429 once with stronger backoff
    #    - Respect IkosTech 1 request/second limit
    #    - Deduplicate readings before upsert
    new_code_fetch = """\
import time
from datetime import datetime, timedelta

def _date_chunks(start_str, end_str, max_days):
    fmt = '%Y-%m-%d'
    start = datetime.strptime(start_str, fmt).date()
    end = datetime.strptime(end_str, fmt).date()
    delta = timedelta(days=max_days)
    td1 = timedelta(days=1)
    cur = start
    while cur <= end:
        yield str(cur), str(min(cur + delta - td1, end))
        cur = cur + delta

MAX_DAYS_PER_CHUNK = 30
RATE_LIMIT_SECONDS = 1.1  # Explicit rate limit per request
RATE_LIMIT_RETRY_SECONDS = 2.2

sensors_plan = bag.get('sensors_plan') or []
if not sensors_plan:
    raise Exception('No sensors in plan (check Build Plan step)')

cfg = {}
try:
    cfg = json.loads(self.remote_id.connection_params or '{}')
except Exception:
    cfg = {}

api_key = (cfg.get('api_key') or '').strip()
if not api_key:
    raise Exception('Missing api_key in connection_params')

headers = {'X-API-Key': api_key}

final_date = fields.Date.today()
readings = []
api_calls = []
errors = []

# Group sensors by serial to share API calls where possible
by_serial = {}
for item in sensors_plan:
    serial = item['serial']
    if serial not in by_serial:
        by_serial[serial] = []
    by_serial[serial].append(item)

for serial, items in by_serial.items():
    min_initial = min(e['initial_date'] for e in items)

    for chunk_start, chunk_end in _date_chunks(min_initial, final_date, MAX_DAYS_PER_CHUNK):
        # Convert YYYY-MM-DD to YYYYMMDD format for API
        from_param = chunk_start.replace('-', '')
        to_param = chunk_end.replace('-', '')

        url = '%s/export/node/%s/data/json/%s/%s' % (
            (base_url or '').rstrip('/'), serial, from_param, to_param)

        resp = request_retry('GET', url, headers=headers, timeout=timeout)
        # IkosTech can return 429 if requests arrive too close together.
        # Retry once with a stronger backoff.
        if resp.status_code == 429:
            time.sleep(RATE_LIMIT_RETRY_SECONDS)
            resp = request_retry('GET', url, headers=headers, timeout=timeout)

        api_calls.append({
            'url': url,
            'method': 'GET',
            'status': resp.status_code,
            'serial': serial,
            'chunk': '%s to %s' % (chunk_start, chunk_end),
        })

        # Apply rate limit AFTER each request
        time.sleep(RATE_LIMIT_SECONDS)

        if resp.status_code >= 400:
            errors.append('API error for serial %s: %s' % (serial, resp.status_code))
            continue

        try:
            payload = resp.json()
        except Exception as e:
            errors.append('JSON parse error for serial %s: %s' % (serial, str(e)))
            continue

        if not isinstance(payload, list):
            errors.append('Invalid response type for serial %s (expected array)' % serial)
            continue

        # payload is a flat array of readings
        for reading in payload:
            if not isinstance(reading, dict):
                continue

            ts_str = reading.get('fecha')
            if not ts_str:
                continue

            # Process each sensor in items (all have same serial, different fields)
            for item in items:
                field = item['field']
                value_raw = reading.get(field)

                if value_raw is None:
                    continue

                try:
                    value = float(value_raw)
                except (ValueError, TypeError):
                    continue

                readings.append({
                    'sensor_id': item['sensor_id'],
                    'value': value,
                    'timestamp': ts_str,
                    'serial': serial,
                    'field': field,
                })

# Deduplicate by (sensor_id, timestamp) keeping the last value in case
# IkosTech returns duplicate rows in the same response window.
dedup_map = {}
for row in readings:
    key = (row.get('sensor_id'), row.get('timestamp'))
    dedup_map[key] = row
readings = dedup_map.values()

bag['readings'] = readings
bag['total_readings'] = len(readings)
bag['api_calls'] = api_calls
if errors:
    bag['fetch_errors'] = errors

result = 'Fetched %d readings from IkosTech' % len(readings)
"""

    # ── 3) Update action: Upsert readings ─────────────────────────────
    #    - Normalize timestamps before searching/creating readings
    #    - Search inactive rows too to avoid unique(name) collisions
    #    - Fallback by computed name to detect ambiguous configurations
    new_code_upsert = """\
from datetime import datetime

Remote = self.remote_id
readings = bag.get('readings') or []
if not readings:
    raise Exception('No readings to upsert')

ReadingModel = env['mdm.measurement.device.sensor.reading'].with_context(
    active_test=False)
SensorModel = env['mdm.measurement.device.sensor']

sensor_ids = list(set([r.get('sensor_id') for r in readings if r.get('sensor_id')]))
sensor_map = {}
if sensor_ids:
    for sensor in SensorModel.browse(sensor_ids):
        sensor_map[sensor.id] = sensor

def _normalize_ts(ts_value):
    if not ts_value:
        return ''
    s = unicode(ts_value).strip().replace('T', ' ')
    if s.endswith('Z'):
        s = s[:-1]
    s = s.replace('/', '-')
    try:
        if len(s) >= 19:
            s = s[:19]
        dt_obj = datetime.strptime(s, '%Y-%m-%d %H:%M:%S')
        return dt_obj.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return s[:19]

upsert_count = 0
upsert_errors = []

for reading in readings:
    sensor_id = reading['sensor_id']
    value = reading['value']
    timestamp_str = _normalize_ts(reading.get('timestamp'))

    if not timestamp_str:
        continue

    try:
        sensor = sensor_map.get(sensor_id)
        if not sensor:
            upsert_errors.append(
                'Sensor not found for sensor_id %s' % sensor_id)
            continue

        # First: exact match by technical key
        existing = ReadingModel.search([
            ('sensor_id', '=', sensor_id),
            ('measurement_time', '=', timestamp_str),
        ], limit=1)

        # Fallback: match by computed unique name (handles inactive rows)
        if not existing:
            unique_name = '%s - %s - %s' % (
                sensor.device_id.name or '',
                sensor.name or '',
                timestamp_str,
            )
            existing = ReadingModel.search([
                ('name', '=', unique_name),
            ], limit=1)

            # Guard against ambiguous configuration: same computed name across
            # different sensors (e.g., duplicate sensor names in one device).
            if existing and existing.sensor_id.id != sensor_id:
                upsert_errors.append(
                    'Name collision for sensor %s at %s. '
                    'Please ensure unique sensor names per device.' % (
                        sensor_id, timestamp_str,
                    )
                )
                continue

        if existing:
            # Update existing record
            existing.write({
                'value': value,
                'remotecontrol_origin_id': Remote.id,
                'active': True,
            })
        else:
            # Create new record
            ReadingModel.create({
                'sensor_id': sensor_id,
                'measurement_time': timestamp_str,
                'value': value,
                'remotecontrol_origin_id': Remote.id,
            })

        upsert_count += 1
    except Exception as e:
        upsert_errors.append(
            'Upsert failed for sensor %d: %s' % (sensor_id, str(e)[:200]))

bag['upsert_count'] = upsert_count
if upsert_errors:
    bag['upsert_errors'] = upsert_errors

result = 'Upserted %d readings' % upsert_count
"""

    # ── 4) Update action: Import elements ─────────────────────────────
    #    - Discover devices from /export/nodes
    #    - Discover real fields by querying each device data endpoint
    #    - Attach JSON with Odoo device/sensor configuration suggestions
    new_code_import_elements = """\
import time
from datetime import datetime, timedelta

Remote = self.remote_id
cfg = {}
try:
    cfg = json.loads(Remote.connection_params or '{}')
except Exception:
    cfg = {}

api_key = (cfg.get('api_key') or '').strip()
if not api_key:
    raise Exception('Missing api_key in connection_params')

headers = {'X-API-Key': api_key}
base = (base_url or '').rstrip('/')

# Step 1: Get list of available devices
url_nodes = base + '/export/nodes'
resp_nodes = request_retry('GET', url_nodes, headers=headers, timeout=timeout)

if resp_nodes.status_code >= 400:
    raise Exception(
        'Failed to fetch /export/nodes: %s %s' % (
            resp_nodes.status_code, (resp_nodes.text or '')[:300]))

try:
    nodes = resp_nodes.json()
except Exception as e:
    raise Exception('Invalid JSON from /export/nodes: %s' % str(e))

if not isinstance(nodes, list):
    raise Exception('Expected array from /export/nodes')

time.sleep(1.1)

# Step 2: Query each device for real data to discover actual fields.
# IkosTech expects dates in YYYYMMDD format in this endpoint.
DISCOVERY_DAYS = 8
today = datetime.utcnow()
date_from_dt = today - timedelta(days=DISCOVERY_DAYS)
date_from = date_from_dt.strftime('%Y-%m-%d')
date_to = today.strftime('%Y-%m-%d')
date_from_param = date_from_dt.strftime('%Y%m%d')
date_to_param = today.strftime('%Y%m%d')

# Metadata fields are useful in diagnostics, but should not create sensor
# configuration suggestions.
METADATA_FIELDS = {
    'fecha', 'serial', 'f', 'fecha_local', 'id', 'device', 'imei', 'operador',
}

# Discover fields for each device
device_fields_map = {}  # {serial: set(field_names)}
all_available_fields = {}  # {field_name: count_found}
device_data_diagnostics = []
device_records_map = {}

for node in nodes:
    if not isinstance(node, dict):
        continue

    serial = str(node.get('serial', ''))
    if not serial:
        continue

    device_fields_map[serial] = set()
    device_records_map[serial] = 0

    # Query device data to discover available fields
    url_data = '%s/export/node/%s/data/json/%s/%s' % (
        base, serial, date_from_param, date_to_param)
    diagnostic = {
        'serial': serial,
        'alias': node.get('alias', ''),
        'url': url_data,
        'from': date_from_param,
        'to': date_to_param,
        'status_code': None,
        'records': 0,
        'sample_keys': [],
        'fields_found': [],
    }
    try:
        resp_data = request_retry('GET', url_data, headers=headers, timeout=timeout)
        time.sleep(1.1)
        diagnostic['status_code'] = resp_data.status_code

        if resp_data.status_code < 400:
            try:
                data_array = resp_data.json()
                if isinstance(data_array, dict):
                    if isinstance(data_array.get('data'), list):
                        data_array = data_array.get('data')
                    elif isinstance(data_array.get('readings'), list):
                        data_array = data_array.get('readings')
                if isinstance(data_array, list):
                    diagnostic['records'] = len(data_array)
                    device_records_map[serial] = len(data_array)
                    sample_keys = []
                    for record in data_array:
                        if not isinstance(record, dict):
                            continue
                        for key in record.keys():
                            if key not in sample_keys:
                                sample_keys.append(key)
                            if key not in METADATA_FIELDS:
                                device_fields_map[serial].add(key)
                    for key in sorted(device_fields_map[serial]):
                        all_available_fields[key] = all_available_fields.get(key, 0) + 1
                    diagnostic['sample_keys'] = sample_keys[:60]
                    diagnostic['fields_found'] = sorted(device_fields_map[serial])
                else:
                    diagnostic['error'] = 'Invalid response type: %s' % (
                        type(data_array).__name__,)
            except Exception as e:
                diagnostic['error'] = 'JSON parse error: %s' % str(e)[:300]
        else:
            diagnostic['error'] = (resp_data.text or '')[:300]
    except Exception as e:
        diagnostic['error'] = 'Request error: %s' % str(e)[:300]
    device_data_diagnostics.append(diagnostic)

# Build elements and sensor config table for easy reference
sensor_config_table = []
elements = []

for node in nodes:
    if not isinstance(node, dict):
        continue

    serial = str(node.get('serial', ''))
    alias = node.get('alias', '')
    device = node.get('device', '')
    estado = node.get('estado', '')

    if not serial:
        continue

    elements.append({
        'serial': serial,
        'alias': alias,
        'device': device,
        'estado': estado,
        'factivacion': node.get('factivacion', ''),
        'factualizacion': node.get('factualizacion', ''),
        'soilType': node.get('soilType', ''),
        'data_records': device_records_map.get(serial, 0),
        'available_fields': sorted(list(device_fields_map.get(serial, set()))),
    })

    # For each field found in this device, create a sensor config suggestion
    for field_name in sorted(device_fields_map.get(serial, set())):
        sensor_config_table.append({
            'serial': serial,
            'alias': alias,
            'field': field_name,
            'odoo_device_params': json.dumps(
                {
                    'serial': serial,
                    'start_date': fields.Date.today(),
                },
                ensure_ascii=True,
            ),
            'odoo_sensor_params': json.dumps(
                {'field': field_name},
                ensure_ascii=True,
            ),
        })

audit = {
    'executed_at': fields.Datetime.now(),
    'total_devices': len(elements),
    'total_unique_fields': len(all_available_fields),
    'total_sensor_suggestions': len(sensor_config_table),
    'query_range': '%s to %s' % (date_from, date_to),
    'api_query_range': '%s to %s' % (date_from_param, date_to_param),
    'devices': elements,
    'all_available_fields': sorted(all_available_fields.keys()),
    'data_diagnostics': device_data_diagnostics,
    'sensor_config_suggestions': sensor_config_table,
}

try:
    audit_json = json.dumps(
        audit, ensure_ascii=True, indent=2, default=str,
    )
    b64 = base64.b64encode(audit_json.encode('utf-8'))
except Exception as json_error:
    simple_audit = {
        'executed_at': str(fields.Datetime.now()),
        'error': str(json_error),
    }
    audit_json = json.dumps(simple_audit, ensure_ascii=True, indent=2)
    b64 = base64.b64encode(audit_json.encode('utf-8'))

fname = 'ikostech_import_elements_%s.json' % (
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
    'res_id': Remote.id,
})

Remote.message_post(
    body=u"[IkosTech] Import elements: %d devices, %d total fields, %d sensor suggestions" % (
        len(elements), len(all_available_fields), len(sensor_config_table)),
    attachment_ids=[att.id],
)

result = 'Imported %d devices with %d fields' % (
    len(elements), len(all_available_fields))
"""

    # ── 5) Update remotecontrol_help ──────────────────────────────────
    new_help = u"""\
<h2>IkosTech · Odoo Integration Help</h2>
<p><strong>Official API:</strong> <code>https://api.ikostech.es/it</code></p>

<hr/>

<h3>1) Connection (Remote Control)</h3>
<p>Type: <code>REST</code> · Base URL: <code>https://api.ikostech.es/it</code></p>
<p>Auth: <code>X-API-Key</code> header</p>
<pre>{
  "api_key": "your_api_key_here"
}</pre>

<h3>2) Device Configuration</h3>
<pre>{
  "serial": "10329694",
  "start_date": "2026-01-01"
}</pre>

<h3>3) Sensor Configuration</h3>
<pre>{
  "field": "hsuelo"
}</pre>
<p>Run <strong>IkosTech: Import elements</strong> to generate a JSON with devices and available sensor field suggestions.</p>

<h3>4) Rate Limiting</h3>
<p>IkosTech strictly enforces <strong>1 request per second per API key</strong>. The fetch and import actions apply a 1.1 second delay and retry HTTP 429 responses.</p>

<h3>5) Changelog</h3>
<ul>
  <li><strong>1.0.1</strong> (2026-06-23)
    <ul>
      <li>Added real field discovery procedure using <code>/export/nodes</code> and device data endpoints.</li>
      <li>Added 429 retry/backoff and explicit 1.1s API delay.</li>
      <li>Improved upsert handling for inactive rows, duplicate payload rows, and computed-name collisions.</li>
    </ul>
  </li>
</ul>
"""

    try:
        action_plan = env.ref(
            '%s.remotecontrol_ikostech_action_build_plan' % MODULE)
        action_plan.write({
            'code': new_code_build_plan,
            'rate_limit_seconds': 0.0,
            'readonly': True,
        })
    except Exception:
        pass

    try:
        action_fetch = env.ref(
            '%s.remotecontrol_ikostech_action_fetch' % MODULE)
        action_fetch.write({
            'code': new_code_fetch,
            'rate_limit_seconds': 1.1,
            'max_retries': 2,
            'readonly': True,
        })
    except Exception:
        pass

    try:
        action_upsert = env.ref(
            '%s.remotecontrol_ikostech_action_upsert' % MODULE)
        action_upsert.write({
            'code': new_code_upsert,
            'rate_limit_seconds': 0.0,
            'readonly': False,
        })
    except Exception:
        pass

    try:
        action_import = env.ref(
            '%s.remotecontrol_ikostech_action_import_elements' % MODULE)
        action_import.write({
            'code': new_code_import_elements,
            'rate_limit_seconds': 1.1,
            'max_retries': 2,
            'readonly': True,
        })
    except Exception:
        pass

    try:
        remote = env.ref('%s.remotecontrol_ikostech' % MODULE)
        remote.write({
            'base_url': 'https://api.ikostech.es/it',
            'timeout': 60,
            'verify_ssl': True,
            'rate_limit_seconds': 1.1,
            'max_retries': 2,
            'backoff': 1.5,
            'readonly': True,
            'remotecontrol_help': new_help,
        })
    except Exception:
        pass

    try:
        procedure = env.ref('%s.remotecontrol_ikostech_procedure' % MODULE)
        procedure.write({
            'schedule_cron': True,
            'readonly': False,
            'interval_number': 1,
            'interval_type': 'days',
            'numbercall': -1,
            'procedure_for_readings': True,
        })
    except Exception:
        pass

    try:
        procedure_import = env.ref(
            '%s.remotecontrol_ikostech_procedure_import_elements' % MODULE)
        procedure_import.write({
            'schedule_cron': False,
            'readonly': True,
            'procedure_for_readings': False,
        })
    except Exception:
        pass
