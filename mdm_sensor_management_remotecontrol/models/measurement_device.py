# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class MeasurementDevice(models.Model):
    _inherit = 'mdm.measurement.device'

    remotecontrol_id = fields.Many2one(
        string='Remotecontrol',
        comodel_name='remotecontrol',
    )

    remotecontrol_params = fields.Text(
        string='Remotecontrol Parameters',
    )

    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        existing_records = self.with_context(active_test=False).search(
            [('name', 'like', self.name + '%')])
        number_of_existing_records = 0
        if existing_records:
            number_of_existing_records = len(existing_records)
        number_of_existing_records = number_of_existing_records + 1
        default['name'] = \
            self.name + ' (' + str(number_of_existing_records) + ')'
        if self.sensor_ids:
            sensor_vals = []
            for sensor in self.sensor_ids:
                sensor_vals.append((0, 0, {
                    'name': sensor.name,
                    'description': sensor.description,
                    'type_id': sensor.type_id.id,
                    'remotecontrol_params': sensor.remotecontrol_params,
                }))
            default['sensor_ids'] = sensor_vals
        return super(MeasurementDevice, self).copy(default)
