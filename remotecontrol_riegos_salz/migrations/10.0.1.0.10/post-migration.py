# -*- coding: utf-8 -*-
# Copyright 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from lxml import etree

from odoo import api, SUPERUSER_ID
from odoo.modules.module import get_module_resource


_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    _logger.info(
        'remotecontrol_riegos_salz post-migration 10.0.1.0.10 started'
    )
    env = api.Environment(cr, SUPERUSER_ID, {})
    module = 'remotecontrol_riegos_salz'
    xmlid = 'remotecontrol_riegos_salz_action_get_readings'
    tree = etree.parse(get_module_resource(module, 'data', 'data.xml'))
    node = tree.xpath('//record[@id="%s"]/field[@name="code"]' % xmlid)[0]
    action = env.ref('%s.%s' % (module, xmlid), raise_if_not_found=False)
    if action:
        action.write({'code': node.text})
        _logger.info('Updated %s code from data.xml', xmlid)
    _logger.info(
        'remotecontrol_riegos_salz post-migration 10.0.1.0.10 completed'
    )
