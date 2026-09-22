# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Add 'atlas' and 'atlas_sensor' endpoints to Daily Sync 'Get Readings' action."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    action = env.ref(
        'remotecontrol_regaber.'
        'remotecontrol_regaber_action_get_readings',
        raise_if_not_found=False)
    if not action or "'atlas_sensor':" in action.code:
        return
    old_entry = (
        "endpoint_map = {\n"
        "    'skyreg': '/SKYreg/WaterMeter/LastValue/',\n"
        "    'skyreg_hydrant': '/SKYreg/Hydrant/WaterMeter/LastValue/',\n"
        "    'skymeter_nbiot': '/SKYmeterNBIoT/WaterMeter/LastValue/',\n"
        "}\n"
    )
    new_entry = (
        "endpoint_map = {\n"
        "    'skyreg': '/SKYreg/WaterMeter/LastValue/',\n"
        "    'skyreg_hydrant': '/SKYreg/Hydrant/WaterMeter/LastValue/',\n"
        "    'skymeter_nbiot': '/SKYmeterNBIoT/WaterMeter/LastValue/',\n"
        "    'atlas': '/Atlas/WaterMeter/LastValue',\n"
        "    'atlas_sensor': '/Atlas/Sensor/LastValue',\n"
        "}\n"
    )
    if old_entry in action.code:
        action.write({'code': action.code.replace(old_entry, new_entry, 1)})
