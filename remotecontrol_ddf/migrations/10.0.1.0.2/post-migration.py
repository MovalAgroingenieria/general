# -*- coding: utf-8 -*-
# Copyright 2026 Moval Agroingenieria
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from lxml import etree

from odoo import SUPERUSER_ID, api
from odoo.modules.module import get_module_resource

_logger = logging.getLogger(__name__)


def _get_field_from_xml(record_id, field_name):
    """Read the same source as new installations, without duplicating action code."""
    resource = get_module_resource('remotecontrol_ddf', 'data', 'data.xml')
    if not resource:
        raise RuntimeError('Cannot locate remotecontrol_ddf/data/data.xml')
    document = etree.parse(resource)
    for record in document.xpath('//record[@id="%s"]' % record_id):
        for field in record.xpath('./field[@name="%s"]' % field_name):
            return field.text or ''
    raise RuntimeError('Missing XML field %s.%s' % (record_id, field_name))


def migrate(cr, version):
    if not version:
        return
    _logger.info('remotecontrol_ddf post-migration 10.0.1.0.2 started')
    env = api.Environment(cr, SUPERUSER_ID, {})

    action = env.ref('remotecontrol_ddf.remotecontrol_ddf_action_get_plots')
    action.write({
        'code': _get_field_from_xml('remotecontrol_ddf_action_get_plots', 'code'),
    })

    remote = env.ref('remotecontrol_ddf.remotecontrol_ddf')
    remote.write({
        'remotecontrol_help': _get_field_from_xml('remotecontrol_ddf', 'remotecontrol_help'),
    })
    # Only updates the code and help; preserves connection_params, base_url,
    # devices, sensors, readings and any user-configured cron schedule.
    _logger.info('remotecontrol_ddf post-migration 10.0.1.0.2 completed')
