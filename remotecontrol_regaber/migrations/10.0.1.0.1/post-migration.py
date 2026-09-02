# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    action = env.ref(
        'remotecontrol_regaber.'
        'remotecontrol_regaber_action_get_last_readings',
        raise_if_not_found=False)
    if not action or "'atlas':" in action.code:
        return
    old_entry = (
        "    'skymeter_nbiot': "
        "'/SKYmeterNBIoT/WaterMeter/LastValue/',\n"
    )
    new_entry = old_entry + (
        "    'atlas': '/Atlas/WaterMeter/LastValue',\n"
    )
    if old_entry in action.code:
        action.write({'code': action.code.replace(old_entry, new_entry, 1)})