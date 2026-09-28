# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# Backport to 10.0 of OCA/server-tools bus_alt_connection

import os
import json
import logging
import select

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

import odoo
from odoo.tools import config
from odoo.addons.bus.models.bus import hashable, TIMEOUT
import odoo.addons.bus.models.bus
import odoo.addons.bus.controllers.main

_logger = logging.getLogger(__name__)


def _connection_info_for(db_name):
    db_or_uri, connection_info = odoo.sql_db.connection_info_for(db_name)
    for p in ('host', 'port'):
        cfg = (os.environ.get('ODOO_IMDISPATCHER_DB_%s' % p.upper())
               or config.get('imdispatcher_db_' + p))
        if cfg:
            connection_info[p] = cfg
    return connection_info


class ImDispatch(odoo.addons.bus.models.bus.ImDispatch):
    def loop(self):
        """ Dispatch postgres notifications
            LISTENing on a direct connection. """
        _logger.info("Bus.loop listen imbus on db postgres (alt connection)")
        conn = psycopg2.connect(**_connection_info_for('postgres'))
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        with conn.cursor() as cr:
            cr.execute("listen imbus")
            conn.commit()
            while True:
                if select.select([conn], [], [], TIMEOUT) == ([], [], []):
                    pass
                else:
                    conn.poll()
                    channels = []
                    while conn.notifies:
                        channels.extend(
                            json.loads(conn.notifies.pop().payload))
                    events = set()
                    for channel in channels:
                        events.update(self.channels.pop(hashable(channel), []))
                    for event in events:
                        event.set()


odoo.addons.bus.models.bus.ImDispatch = ImDispatch

if not odoo.multi_process or odoo.evented:
    dispatch = ImDispatch()
    odoo.addons.bus.models.bus.dispatch = dispatch
    odoo.addons.bus.controllers.main.dispatch = dispatch
