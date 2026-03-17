# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    MODULE = 'remotecontrol_sentilo_aca'

    # Fix "Get devices (plan)" action: remove +timedelta(days=1) from
    # initial_date calculation. Safe because upsert handles duplicates.

    new_code = """\
from datetime import timedelta

Remote = self.remote_id
Sensor = env['mdm.measurement.device.sensor']
today_str = fields.Date.today()

condition = [
    ('remotecontrol_params', '!=', False),
    ('device_id.remotecontrol_id', '=', Remote.id),
]

if selected_device_ids:
    condition.append(('device_id', 'in', selected_device_ids))

sensors = Sensor.search(condition)
plan = []

for sensor in sensors:
    try:
        cfg = json.loads(sensor.remotecontrol_params or '{}') or {}
    except Exception:
        cfg = {}

    sensor_code = (cfg.get('sensor') or '').strip()
    provider = (cfg.get('provider') or '').strip()

    if not sensor_code or not provider:
        continue

    last_reading = env['mdm.measurement.device.sensor.reading'].search(
        [
            ('sensor_id', '=', sensor.id),
            ('active', '=', True),
        ],
        order='measurement_time desc',
        limit=1,
    )

    if last_reading:
        dt = fields.Datetime.from_string(last_reading.measurement_time)
        initial_date = dt.strftime('%d/%m/%Y')
    else:
        year_str = today_str[:4]
        initial_date = '01/01/%s' % year_str

    plan.append({
        'sensor_id': sensor.id,
        'device_id': sensor.device_id.id,
        'sensor_code': sensor_code,
        'provider': provider,
        'initial_date': initial_date,
    })

bag['sensors_plan'] = plan
"""

    xmlid = '%s.remotecontrol_sentilo_aca_action_get_devices' % MODULE
    action = env.ref(xmlid, raise_if_not_found=False)
    if action:
        action.write({'code': new_code})
