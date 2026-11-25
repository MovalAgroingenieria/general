# -*- coding: utf-8 -*-
# Copyright 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from lxml import etree

from odoo import SUPERUSER_ID, api
from odoo.modules.module import get_module_resource


_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    module = 'remotecontrol_microcom'
    tree = etree.parse(get_module_resource(module, 'data', 'data.xml'))
    action_ids = (
        'remotecontrol_microcom_action_get_token',
        'remotecontrol_microcom_action_get_readings',
    )
    for xmlid in action_ids:
        action = env.ref('%s.%s' % (module, xmlid))
        node = tree.xpath('//record[@id="%s"]/field[@name="code"]' % xmlid)[0]
        action.write({'code': node.text})
        _logger.info('Updated MICROCOM action %s', xmlid)
