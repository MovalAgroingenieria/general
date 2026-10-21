# -*- coding: utf-8 -*-
# 2026 Moval Agroingenieria
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from lxml import etree
from odoo import api, SUPERUSER_ID
from odoo.modules.module import get_module_resource


def migrate(cr, version):
    """Refresh only the shipped actions and help despite noupdate=1."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    module = 'remotecontrol_riegos_salz'
    path = get_module_resource(module, 'data', 'data.xml')
    tree = etree.parse(path)
    action_ids = (
        'remotecontrol_riegos_salz_action_get_devices',
        'remotecontrol_riegos_salz_action_get_readings',
        'remotecontrol_riegos_salz_action_import_elements',
    )
    for xmlid in action_ids:
        action = env.ref('%s.%s' % (module, xmlid))
        node = tree.xpath('//record[@id="%s"]/field[@name="code"]' % xmlid)[0]
        action.write({'code': node.text})
    remote = env.ref('%s.remotecontrol_riegos_salz' % module)
    node = tree.xpath('//record[@id="remotecontrol_riegos_salz"]/'
                      'field[@name="remotecontrol_help"]')[0]
    remote.write({'remotecontrol_help': node.text})
