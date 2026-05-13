# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return

    module = 'remotecontrol_hidroconta'
    env = api.Environment(cr, SUPERUSER_ID, {})
    remote = env.ref(
        '%s.remotecontrol_hidroconta' % module,
        raise_if_not_found=False,
    )
    if remote and remote.remotecontrol_help:
        help_content = remote.remotecontrol_help
        help_content = help_content.replace(
            'with (element_id, subtype, subcode, start_date) for each '
            'configured sensor.',
            'with (element_id, subtype, subcode, start_date, '
            'conversion_factor) for each configured sensor.',
        )
        help_content = help_content.replace(
            'The numeric value from <code>value</code> field is stored.',
            'The numeric value from <code>value</code> field is multiplied '
            'by <code>conversion_factor</code> and stored.',
        )
        help_content = help_content.replace(
            'Verify that each sensor in Odoo has the proper '
            '<code>element_id</code>, <code>subtype</code>, and '
            '<code>subcode</code> defined.',
            'Verify that each sensor in Odoo has the proper '
            '<code>element_id</code>, <code>subtype</code>, and '
            '<code>subcode</code> defined. <code>conversion_factor</code> '
            'is optional and defaults to <code>1.0</code> when missing.',
        )
        help_content = help_content.replace(
            '"subcode": 0,\n}</pre>',
            '"subcode": 0\n}</pre>',
        )
        help_content = help_content.replace(
            '<li><code>conversion_factor</code>: Multiplier applied to each '
            'received reading value (default: 1.0)</li>',
            '<li><code>conversion_factor</code>: Optional multiplier applied '
            'to each received reading value (default: 1.0 when missing)</li>',
        )
        remote.write({'remotecontrol_help': help_content})

    action = env.ref(
        '%s.remotecontrol_hidroconta_action_build_sensor_plan' % module,
        raise_if_not_found=False,
    )
    if action:
        action_code = """\
Remote = self.remote_id
Sensor = env['mdm.measurement.device.sensor']
condition = [
    ('remotecontrol_params', '!=', False),
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
    conversion_factor = sensor_cfg.get('conversion_factor')
    if conversion_factor in (None, ''):
        conversion_factor = 1.0
    try:
        conversion_factor = float(conversion_factor)
    except Exception:
        conversion_factor = 1.0
    if not element_id or subtype is None:
        continue
    plan_item = {
        'odoo_sensor_id': sensor.id,
        'element_id': element_id,
        'subtype': subtype,
        'subcode': subcode,
        'start_date': start_date,
        'conversion_factor': conversion_factor
    }
    sensor_plan.append(plan_item)
bag['sensor_plan'] = sensor_plan
result = 'Built sensor plan with %d sensors' % len(sensor_plan)
"""
        action.write({'code': action_code})
