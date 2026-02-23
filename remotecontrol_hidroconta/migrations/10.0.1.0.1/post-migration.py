# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    """Set procedure_for_readings = True and patch action codes."""
    try:
        procedure = env.ref('remotecontrol_hidroconta.'
                            'remotecontrol_hidroconta_procedure_daily_sync')
        procedure.write({'procedure_for_readings': True})
    except Exception:
        pass
    # Patch action: remotecontrol_hidroconta_action_build_sensor_plan
    try:
        action = env.ref('remotecontrol_hidroconta.remotecontrol_hidroconta_'
                         'action_build_sensor_plan')
        action.write({
            'code': '''
Remote = self.remote_id
Sensor = env['mdm.measurement.device.sensor']
condition = [
    ('remotecontrol_params','!=',False),
    ('device_id.remotecontrol_id', '=', Remote.id),
    ('active', '=', True)
]
if selected_device_ids:
    condition.append(('device_id', 'in', selected_device_ids))
sensors = Sensor.search(condition)
sensor_plan = []
for sensor in sensors:
    device = sensor.device_id
    try:
        sensor_cfg = json.loads(sensor.remotecontrol_params or '{}') or {}
    except Exception:
        sensor_cfg = {}
    try:
        device_cfg = json.loads(device.remotecontrol_params or '{}') or {}
    except Exception:
        device_cfg = {}
    element_id = sensor_cfg.get('element_id') or device_cfg.get('element_id')
    subtype = sensor_cfg.get('subtype') or device_cfg.get('subtype')
    subcode = sensor_cfg.get('subcode') or device_cfg.get('subcode', 0)
    start_date = sensor_cfg.get('start_date') or device_cfg.get(
        'start_date', '2025-01-01')
    if not element_id or subtype is None:
        continue
    plan_item = {
        'odoo_sensor_id': sensor.id,
        'element_id': element_id,
        'subtype': subtype,
        'subcode': subcode,
        'start_date': start_date
    }
    sensor_plan.append(plan_item)
bag['sensor_plan'] = sensor_plan
result = 'Built sensor plan with %d sensors' % len(sensor_plan)
''',
        })
    except Exception:
        pass
