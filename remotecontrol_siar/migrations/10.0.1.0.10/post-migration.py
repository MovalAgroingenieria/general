# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, SUPERUSER_ID


_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Replace the two action scripts without changing noupdate or settings."""
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    MODULE = 'remotecontrol_siar'

    # Keep these scripts self-contained, as in previous SiAR migrations.
    # The plan treats start_date as a lower bound, even with existing readings.
    # Readings wait before each request and audit only sensor values and errors.
    new_code = """\
import json
import base64
import time
import pytz
from datetime import datetime

remotecontrol = self.remote_id
plan = bag.get('sensors_plan') or []

total_upserts = 0
total_errors = 0
items = []

spanish_tz = pytz.timezone('Europe/Madrid')
utc_tz = pytz.timezone('UTC')

for sensor_plan in plan:
    siar_token = sensor_plan.get('siar_token') or ''
    sensor_id = sensor_plan['sensor_id']
    device_id = sensor_plan['device_id']
    station = sensor_plan['station']
    magnitude = sensor_plan['magnitude']
    initial_date = sensor_plan['initial_date']
    final_date = sensor_plan['final_date']

    endpoint = (
        (remotecontrol.base_url or '').rstrip('/')
        + '/Datos/Diarios/ESTACION'
    )

    item = {
        'sensor_id': sensor_id,
        'device_id': device_id,
        'station': station,
        'magnitude': magnitude,
        'requested_initial_date': initial_date,
        'requested_final_date': final_date,
        'status': None,
        'points_found': None,
        'data_field_is_null': None,
        'magnitude_missing_count': 0,
        'magnitude_null_count': 0,
        'skipped_empty_value': 0,
        'upserts': 0,
        'errors': 0,
        'readings': [],
    }

    try:
        if not siar_token:
            raise ValueError(
                'El plan del sensor no contiene token de SiAR.'
            )

        url_request = (
            endpoint
            + '?Id=%s&FechaInicial=%s&FechaFinal=%s&token=%s'
            % (
                station,
                initial_date,
                final_date,
                siar_token,
            )
        )

        # Tambien separa la primera consulta de la autenticacion.
        time.sleep(60)

        resp = request_retry(
            'GET',
            url_request,
            timeout=timeout,
        )

        code = resp.status_code
        item['status'] = code

        try:
            payload = resp.json()
        except ValueError:
            raise ValueError(
                'SiAR no devuelve JSON valido. HTTP %s' % code
            )

        if not isinstance(payload, dict):
            raise ValueError(
                'SiAR devuelve un JSON que no es un objeto. HTTP %s'
                % code
            )

        message = payload.get('MensajeRespuesta')
        server_error = payload.get('error')

        if message:
            item['api_message'] = (u'%s' % message).replace(
                siar_token, '[TOKEN]'
            )

        if code >= 400:
            error_detail = (
                message
                or server_error
                or 'Sin mensaje del servidor'
            )
            raise ValueError(
                u'SiAR HTTP %s: %s' % (code, error_detail)
            )

        if 'datos' in payload:
            data_list = payload['datos']
        elif 'Datos' in payload:
            data_list = payload['Datos']
        else:
            raise ValueError(
                'La respuesta no contiene el campo datos ni Datos.'
            )

        item['data_field_is_null'] = data_list is None

        if data_list is None:
            data_list = []

        if not isinstance(data_list, list):
            raise ValueError(
                'El campo de datos no es una lista.'
            )

        if not all(isinstance(row, dict) for row in data_list):
            raise ValueError(
                'La lista contiene elementos que no son objetos.'
            )

        item['points_found'] = len(data_list)

        for reading in data_list:
            if magnitude not in reading:
                item['magnitude_missing_count'] += 1
                continue

            raw_value = reading[magnitude]

            if raw_value is None:
                item['magnitude_null_count'] += 1
                continue

            if (
                isinstance(raw_value, basestring)
                and raw_value.strip().lower() in ('', 'null')
            ):
                item['skipped_empty_value'] += 1
                continue

            try:
                value = float(raw_value)
                siar_datetime = datetime.strptime(
                    reading['Fecha'],
                    '%Y-%m-%dT%H:%M:%S',
                )
                utc_dt = spanish_tz.localize(
                    siar_datetime
                ).astimezone(utc_tz)
                measurement_time = fields.Datetime.to_string(
                    utc_dt
                )
            except (ValueError, TypeError, KeyError) as error:
                item['errors'] += 1
                error_text = (u'%s' % error).replace(
                    siar_token, '[TOKEN]'
                )
                item['readings'].append({
                    'api_date': reading.get('Fecha'),
                    'error': error_text,
                })
                continue

            env.cr.execute('SAVEPOINT siar_reading_upsert')
            try:
                remotecontrol.upsert(
                    'mdm.measurement.device.sensor.reading',
                    {
                        'sensor_id': sensor_id,
                        'measurement_time': measurement_time,
                    },
                    {
                        'remotecontrol_origin_id': remotecontrol.id,
                        'value': value,
                    },
                )
            except Exception as error:
                env.cr.execute(
                    'ROLLBACK TO SAVEPOINT siar_reading_upsert'
                )
                item['errors'] += 1
                error_text = (u'%s' % error).replace(
                    siar_token, '[TOKEN]'
                )
                item['readings'].append({
                    'api_date': reading.get('Fecha'),
                    'error': error_text,
                })
            else:
                item['upserts'] += 1
                item['readings'].append({
                    'api_date': reading.get('Fecha'),
                    'measurement_time': measurement_time,
                    'value': value,
                })
            finally:
                env.cr.execute(
                    'RELEASE SAVEPOINT siar_reading_upsert'
                )

    except Exception as error:
        item['errors'] += 1

        if item['status'] is None:
            item['status'] = -1

        error_text = u'%s' % error
        if siar_token:
            error_text = error_text.replace(
                siar_token, '[TOKEN]'
            )

        item['error'] = error_text

    total_upserts += item['upserts']
    total_errors += item['errors']
    items.append(item)

local_dt = fields.Datetime.to_string(
    fields.Datetime.context_timestamp(
        self,
        fields.Datetime.from_string(fields.Datetime.now()),
    )
)

audit = {
    'executed_at': local_dt,
    'script_version': 'siar-readings-clean-1',
    'total_upserts': total_upserts,
    'total_errors': total_errors,
    'items': items,
}

audit_json = json.dumps(
    audit,
    ensure_ascii=True,
    indent=2,
)

filename = 'readings_fetch_%s.json' % (
    local_dt.replace('-', '').replace(' ', '_').replace(':', '')
)

attachment = env['ir.attachment'].create({
    'name': filename,
    'datas_fname': filename,
    'datas': base64.b64encode(audit_json.encode('utf-8')),
    'mimetype': 'application/json',
    'res_model': 'remotecontrol',
    'res_id': remotecontrol.id,
})

remotecontrol.message_post(
    body=u'[Readings] upserts=%s errors=%s' % (
        total_upserts,
        total_errors,
    ),
    attachment_ids=[attachment.id],
)

bag['upserts'] = total_upserts
bag['errors'] = total_errors
bag['audit_attachment_id'] = attachment.id
"""

    new_code_devices = """\
import json
from datetime import datetime, timedelta

plan = []
siar_token = bag.get('siar_token')

if not siar_token:
    raise ValueError(
        'No hay token de SiAR. Ejecuta el procedimiento completo.'
    )

condition = [
    ('remotecontrol_id', '=', self.remote_id.id),
]

if selected_device_ids:
    condition.append(('id', 'in', selected_device_ids))

devices = env['mdm.measurement.device'].search(condition)

if not devices:
    raise ValueError(
        'No hay dispositivos SiAR para la seleccion indicada.'
    )

yesterday_str = (
    datetime.strptime(fields.Date.today(), '%Y-%m-%d')
    - timedelta(days=1)
).strftime('%Y-%m-%d')

default_initial_date = yesterday_str[:7] + '-01'
default_final_date = yesterday_str

all_sensor_ids = []
for device in devices:
    all_sensor_ids.extend(sensor.id for sensor in device.sensor_ids)

last_readings_map = {}

if all_sensor_ids:
    env.cr.execute(
        'SELECT DISTINCT ON (sensor_id) sensor_id, measurement_time '
        'FROM mdm_measurement_device_sensor_reading '
        'WHERE sensor_id IN %s AND active = TRUE '
        'ORDER BY sensor_id, measurement_time DESC',
        (tuple(all_sensor_ids),)
    )

    for sensor_id, measurement_time in env.cr.fetchall():
        last_readings_map[sensor_id] = measurement_time

for device in devices:
    device_cfg = json.loads(device.remotecontrol_params or '{}')

    if not isinstance(device_cfg, dict):
        raise ValueError(
            'Los parametros del dispositivo %s deben ser un objeto JSON.'
            % device.id
        )

    station = (device_cfg.get('station') or '').strip()

    if not station:
        raise ValueError(
            'Falta station en los parametros del dispositivo %s.'
            % device.id
        )

    configured_start = (
        device_cfg.get('start_date') or ''
    ).strip()

    if configured_start:
        configured_start = datetime.strptime(
            configured_start,
            '%Y-%m-%d',
        ).strftime('%Y-%m-%d')

    for sensor in device.sensor_ids:
        sensor_cfg = json.loads(
            sensor.remotecontrol_params or '{}'
        )

        if not isinstance(sensor_cfg, dict):
            raise ValueError(
                'Los parametros del sensor %s deben ser un objeto JSON.'
                % sensor.id
            )

        magnitude = (
            sensor_cfg.get('magnitude') or ''
        ).strip()

        if not magnitude:
            continue

        last_reading_time = last_readings_map.get(sensor.id)
        last_reading_date = None

        if last_reading_time:
            if hasattr(last_reading_time, 'strftime'):
                last_reading_date = last_reading_time.strftime(
                    '%Y-%m-%d'
                )
            else:
                last_reading_date = fields.Date.to_string(
                    fields.Datetime.from_string(last_reading_time)
                )

        if configured_start and last_reading_date:
            start_date = max(
                configured_start,
                last_reading_date,
            )
        elif configured_start:
            start_date = configured_start
        elif last_reading_date:
            start_date = last_reading_date
        else:
            start_date = default_initial_date

        end_date = default_final_date

        if start_date > end_date:
            continue

        plan.append({
            'siar_token': siar_token,
            'device_id': device.id,
            'sensor_id': sensor.id,
            'station': station,
            'magnitude': magnitude,
            'initial_date': start_date,
            'final_date': end_date,
        })

bag['sensors_plan'] = plan
"""

    actions = (
        ('remotecontrol_siar_action_get_readings', new_code),
        ('remotecontrol_siar_action_get_devices', new_code_devices),
    )
    for xmlid, code in actions:
        action = env.ref('%s.%s' % (MODULE, xmlid))
        action.write({'code': code})
        _logger.info('Updated SiAR action %s despite noupdate=1.', xmlid)
