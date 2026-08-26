# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    MODULE = 'remotecontrol_regacom'

    xmlid = '%s.remotecontrol_regacom_procedure_irrigation_events' % MODULE
    if env.ref(xmlid, raise_if_not_found=False):
        return

    remote = env.ref(
        '%s.remotecontrol_regacom' % MODULE, raise_if_not_found=False)
    if not remote:
        return

    action_code = """\
# Get irrigation events (consumption data) from historico_iru and create wua.irrigationevent records
# Fetches from last event date or first day of current month
import logging
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)
Remote = self.remote_id
WaterConnection = env['wua.waterconnection']
IrrigationEvent = env['wua.waterconnection.irrigation.event']

# Connect to Regacom database
logger.info('REGACOM irrigation_events(xml): connecting to SQL')
try:
    cursor = sql_connect()
    logger.info('REGACOM irrigation_events(xml): SQL connection established')
except Exception as conn_error:
    logger.error('REGACOM irrigation_events(xml): SQL connection failed: %s', str(conn_error))
    raise
bag['_sql_cursor'] = cursor

try:
    # Wrap all ORM operations in savepoint to handle transaction state
    with self.env.cr.savepoint():
        # Get waterconnections that are configured for irrigation event import
        waterconnections = WaterConnection.search([
            ('telecontrol_associated', '=', 'regacom'),
            ('irrigationshed_id.regacom_enabled', '=', True),
            ('irrigationshed_id.regacom_import_irrigation_events', '=', True),
            ('irrigationshed_id.regacom_diriru', '!=', False),
        ])
        logger.info('REGACOM irrigation_events(xml): waterconnections=%s',
                    len(waterconnections))

        allowed_diriru = sorted(set(
            waterconnections.mapped('irrigationshed_id.regacom_diriru')))
        logger.info('REGACOM irrigation_events(xml): allowed_diriru=%s',
                    allowed_diriru)

        total_events_created = 0
        total_events_skipped = 0

        if allowed_diriru:
            # Determine start date: last event irrigation_end_date or first day of current month
            today = fields.Date.today()
            first_day_month = '%s-01' % today[:7]

            # Check if there are existing irrigation events
            last_event = IrrigationEvent.search(
                [('irrigation_end_date', '!=', False)],
                order='irrigation_end_date desc',
                limit=1
            )
            start_date = last_event.irrigation_end_date.split()[0] if last_event else first_day_month
            logger.info('REGACOM irrigation_events(xml): start_date=%s', start_date)

        diriru_placeholders = ', '.join(['?'] * len(allowed_diriru))
        query = '''
            SELECT
                HIRU_nDirUM,
                HIRU_nDirIRU,
                HIRU_nNumero_contador,
                HIRU_nFechaHora,
                CAST(HIRU_nConsumo AS FLOAT) AS HIRU_nConsumo
            FROM historico_iru
            WHERE HIRU_nConsumo > 0
              AND HIRU_nDirUM IS NOT NULL
              AND HIRU_nDirIRU IS NOT NULL
              AND HIRU_nDirIRU IN ({diriru_placeholders})
              AND HIRU_nNumero_contador IS NOT NULL
              AND HIRU_nFechaHora >= ?
            ORDER BY HIRU_nDirUM, HIRU_nDirIRU,
                     HIRU_nNumero_contador, HIRU_nFechaHora ASC
        '''.format(diriru_placeholders=diriru_placeholders)

        params = list(allowed_diriru) + [start_date + ' 00:00:00']
        sql_execute(cursor, query, tuple(params))
        rows = sql_fetchall(cursor)
        logger.info('REGACOM irrigation_events(xml): rows=%s', len(rows))

        wc_map = {}
        for wc in waterconnections:
            dir_iru = wc.irrigationshed_id.regacom_diriru
            if dir_iru not in wc_map:
                wc_map[dir_iru] = []
            wc_map[dir_iru].append(wc)
        for row in rows:
            dir_um = row[0]
            dir_iru = row[1]
            numero_contador = row[2]
            fecha_hora = str(row[3]) if row[3] else None  # timestamp format
            consumo = float(row[4]) if row[4] is not None else 0.0

            if dir_iru in wc_map:
                for wc in wc_map[dir_iru]:
                    try:
                        with self.env.cr.savepoint():
                            event_date = fecha_hora[:10] if fecha_hora else None
                            existing = IrrigationEvent.search([
                                ('waterconnection_id', '=', wc.id),
                                ('irrigation_volume', '=', consumo),
                            ], limit=1)

                            if existing:
                                event_date_only = event_date
                                existing_date_only = existing.irrigation_end_date.split()[0]
                                if event_date_only != existing_date_only:
                                    existing = False

                            if not existing:
                                event_datetime = fecha_hora if fecha_hora else (event_date + ' 12:00:00')

                                try:
                                    if isinstance(event_datetime, str):
                                        dt_obj = datetime.strptime(event_datetime[:19], '%Y-%m-%d %H:%M:%S')
                                    else:
                                        dt_obj = event_datetime
                                    madrid_tz = pytz.timezone('Europe/Madrid')
                                    dt_localized = madrid_tz.localize(dt_obj)
                                    dt_utc = dt_localized.astimezone(pytz.timezone('UTC'))
                                    event_datetime_utc = dt_utc.strftime('%Y-%m-%d %H:%M:%S')
                                except Exception as e:
                                    logger.warning('REGACOM irrigation_events(xml): Failed to convert timezone for %s: %s',
                                                  event_datetime, str(e))
                                    event_datetime_utc = event_datetime

                                IrrigationEvent.create({
                                    'waterconnection_id': wc.id,
                                    'irrigation_start_date': event_datetime_utc,
                                    'irrigation_end_date': event_datetime_utc,
                                    'irrigation_volume': consumo,
                                })
                                total_events_created += 1
                            else:
                                total_events_skipped += 1
                    except Exception as e:
                        logger.warning('REGACOM irrigation_events(xml): Failed to create event for wc=%s: %s',
                                      wc.id, str(e))
                        total_events_skipped += 1
        else:
            logger.info(
                'REGACOM irrigation_events(xml): no allowed_diriru found')

    bag['total_irrigation_events_created'] = total_events_created
    bag['total_irrigation_events_skipped'] = total_events_skipped
    logger.info('REGACOM irrigation_events(xml): created=%s skipped=%s',
                total_events_created, total_events_skipped)

except Exception as error:
    logger.exception('REGACOM irrigation_events(xml): SQL/action error')
    raise
finally:
    # Always close the connection
    cursor = bag.get('_sql_cursor')
    if cursor:
        sql_close(cursor)
    logger.info('REGACOM irrigation_events(xml): connection closed')
"""

    action = env['remotecontrol.action'].create({
        'name': 'Regacom: Get Irrigation Events',
        'remote_id': remote.id,
        'active': True,
        'rate_limit_seconds': 0.0,
        'max_retries': 1,
        'backoff': 0,
        'readonly': True,
        'code': action_code,
    })
    env['ir.model.data'].create({
        'name': 'remotecontrol_regacom_action_get_irrigation_events',
        'module': MODULE,
        'model': 'remotecontrol.action',
        'res_id': action.id,
        'noupdate': True,
    })

    procedure = env['remotecontrol.procedure'].create({
        'name': 'Regacom: Get Irrigation Events',
        'remote_id': remote.id,
        'active': True,
        'readonly': True,
    })
    env['ir.model.data'].create({
        'name': 'remotecontrol_regacom_procedure_irrigation_events',
        'module': MODULE,
        'model': 'remotecontrol.procedure',
        'res_id': procedure.id,
        'noupdate': True,
    })

    step = env['remotecontrol.step'].create({
        'name': 'Get Irrigation Events',
        'procedure_id': procedure.id,
        'action_id': action.id,
        'sequence': 10,
    })
    env['ir.model.data'].create({
        'name': 'remotecontrol_regacom_step_get_irrigation_events',
        'module': MODULE,
        'model': 'remotecontrol.step',
        'res_id': step.id,
        'noupdate': True,
    })
