# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Post-migration script to update SCADA Abaran New actions
    Changes:
    1. Update date format in SQL filters from DD/MM/YYYY to YYYY-MM-DD (ISO format)
    2. Add auto-detection for date parsing (supports both ISO and Spanish formats)
    3. Remove IS NOT NULL filter to allow 0 and NULL values
    """
    if not version:
        return

    _logger.info('Updating SCADA Abaran New - Get readings action...')

    # Get the action record
    cr.execute("""
        SELECT id
        FROM remotecontrol_action
        WHERE name = 'SCADA Abaran New: Get readings'
        LIMIT 1
    """)
    result = cr.fetchone()
    if not result:
        _logger.warning('Action "SCADA Abaran New: Get readings" not found')
        return
    action_id = result[0]
    # Updated code with:
    # - ISO date format in SQL filters (YYYY-MM-DD HH:MM:SS)
    # - Auto-detection for date parsing
    # - No IS NOT NULL filter
    new_code = """
# Fetch readings from SCADA Abaran New MariaDB database and upsert into Odoo
Remote = self.remote_id
SensorModel = env['mdm.measurement.device.sensor']
plan = bag.get('sensors_plan') or []

if not plan:
    raise Exception("No sensors in plan. Run 'Get devices (plan)' first.")

final_date = fields.Date.today()
initial_date = None
total_upserts = 0
total_errors = 0
items = []

# Connect to SCADA database and store cursor in bag
cursor = sql_connect()
bag['_sql_cursor'] = cursor

try:
    for sensor_plan in plan:
        sensor_id = sensor_plan['sensor_id']
        device_id = sensor_plan['device_id']
        table_name = sensor_plan['table_name']
        datetime_column = sensor_plan['datetime_column']
        value_column = sensor_plan['value_column']
        initial_date = sensor_plan['initial_date']

        sensor_record = SensorModel.browse(sensor_id)

        try:
            # Use ISO format for date filtering (YYYY-MM-DD HH:MM:SS)
            # This works with both ISO and Spanish date formats in the database
            from datetime import datetime
            initial_dt = datetime.strptime(initial_date, '%Y-%m-%d')
            initial_str = initial_dt.strftime('%Y-%m-%d 00:00:00')

            # Final date with time
            final_dt = datetime.strptime(final_date, '%Y-%m-%d')
            final_str = final_dt.strftime('%Y-%m-%d 23:59:59')

            # Build query (without IS NOT NULL filter - allows 0 and NULL values)
            query = \"\"\"
                SELECT ID_MEDIDA, `%s`, `%s`
                FROM `%s`
                WHERE `%s` >= ?
                  AND `%s` <= ?
                ORDER BY `%s` ASC
            \"\"\" % (
                datetime_column, value_column,
                table_name,
                datetime_column,
                datetime_column,
                datetime_column
            )

            query_params = (
                initial_str,
                final_str
            )

            sql_execute(cursor, query, query_params)
            rows = sql_fetchall(cursor)

            upserts = 0
            errs = 0
            readings_summary = []

            for row in rows:
                try:
                    id_medida = row[0]
                    fecha_hora_value = row[1]
                    raw_value = float(row[2]) if row[2] is not None else 0.0

                    # Parse datetime - auto-detect format (ISO or Spanish)
                    # Supported: YYYY-MM-DD HH:MM:SS[.mmm] or DD/MM/YYYY HH:MM[:SS]
                    if hasattr(fecha_hora_value, 'strftime'):
                        # It's already a datetime object
                        naive_dt = fecha_hora_value
                    else:
                        # It's a string - auto-detect format
                        fecha_str = str(fecha_hora_value).strip()
                        naive_dt = None

                        # Try ISO formats first (YYYY-MM-DD)
                        for fmt in ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M']:
                            try:
                                naive_dt = datetime.strptime(fecha_str, fmt)
                                break
                            except ValueError:
                                continue

                        # Try Spanish formats (DD/MM/YYYY)
                        if naive_dt is None:
                            for fmt in ['%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M']:
                                try:
                                    naive_dt = datetime.strptime(fecha_str, fmt)
                                    break
                                except ValueError:
                                    continue

                        # If still not parsed, raise error
                        if naive_dt is None:
                            raise ValueError('Cannot parse date: %s' % fecha_str)

                    # Convert from Europe/Madrid to UTC
                    madrid_tz = pytz.timezone('Europe/Madrid')
                    local_dt = madrid_tz.localize(naive_dt)
                    utc_dt = local_dt.astimezone(pytz.UTC)
                    timestamp = fields.Datetime.to_string(utc_dt.replace(tzinfo=None))

                    # Upsert reading into Odoo
                    Remote.upsert(
                        'mdm.measurement.device.sensor.reading',
                        {
                            'sensor_id': sensor_record.id,
                            'measurement_time': timestamp
                        },
                        {
                            'value': raw_value,
                            'remotecontrol_origin_id': Remote.id
                        }
                    )
                    upserts += 1

                    # Keep sample for audit (limit to first 10)
                    if len(readings_summary) < 10:
                        readings_summary.append({
                            'id_medida': id_medida,
                            'fecha_hora_original': str(fecha_hora_value),
                            'time_utc': timestamp,
                            'value': raw_value
                        })

                except Exception as e:
                    errs += 1
                    if len(readings_summary) < 10:
                        readings_summary.append({
                            'row': str(row),
                            'error': str(e)
                        })

            total_upserts += upserts
            total_errors += errs

            items.append({
                'sensor_id': sensor_id,
                'device_id': device_id,
                'table_name': table_name,
                'datetime_column': datetime_column,
                'value_column': value_column,
                'status': 'success',
                'points_found': len(rows),
                'upserts': upserts,
                'errors': errs,
                'readings': readings_summary
            })

        except Exception as e:
            total_errors += 1
            items.append({
                'sensor_id': sensor_id,
                'device_id': device_id,
                'table_name': table_name,
                'datetime_column': datetime_column,
                'value_column': value_column,
                'status': 'error',
                'error': str(e)
            })

finally:
    # Always close the connection
    cursor = bag.get('_sql_cursor')
    if cursor:
        sql_close(cursor)

# Create audit attachment
audit = {
    'executed_at': str(fields.Datetime.now()),
    'initial_date': initial_date if plan else None,
    'final_date': final_date,
    'total_upserts': total_upserts,
    'total_errors': total_errors,
    'sensors_processed': len(plan),
    'items': items
}

try:
    audit_json = json.dumps(audit, ensure_ascii=True, indent=2, default=str)
    b64 = base64.b64encode(audit_json.encode('utf-8'))
except Exception as json_error:
    simple_audit = {
        'executed_at': str(fields.Datetime.now()),
        'total_upserts': total_upserts,
        'total_errors': total_errors,
        'error': str(json_error)
    }
    audit_json = json.dumps(simple_audit, ensure_ascii=True, indent=2)
    b64 = base64.b64encode(audit_json.encode('utf-8'))

fname = 'scada_abaran_new_readings_%s.json' % (
    fields.Datetime.now().replace(':', '').replace('-', '').replace(' ', '_')
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
    body="[SCADA Abaran New Readings] upserts=%s errors=%s sensors=%s" % (
        total_upserts, total_errors, len(plan)
    ),
    attachment_ids=[att.id]
)

bag['upserts'] = total_upserts
bag['errors'] = total_errors
bag['audit_attachment_id'] = att.id
"""
    # Update the action code
    cr.execute("""
        UPDATE remotecontrol_action
        SET code = %s
        WHERE id = %s
    """, (new_code, action_id))
    _logger.info('Successfully updated SCADA Abaran New - Get readings action')
