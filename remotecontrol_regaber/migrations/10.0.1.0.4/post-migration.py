# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    action_ids = (
        'remotecontrol_regaber_action_get_last_readings',
        'remotecontrol_regaber_action_get_readings',
    )
    old_code = (
        "        payload = resp.json() or {}\n"
        "        last_value_obj = payload.get('LastValue') or {}\n"
    )
    new_code = (
        "        payload = resp.json() or {}\n"
        "        if isinstance(payload, list):\n"
        "            payload = payload[0] if payload else {}\n"
        "        last_value_obj = payload.get('LastValue') or {}\n"
    )
    for action_id in action_ids:
        action = env.ref(
            'remotecontrol_regaber.%s' % action_id,
            raise_if_not_found=False)
        if action and old_code in action.code:
            action.write({'code': action.code.replace(old_code, new_code, 1)})
    return