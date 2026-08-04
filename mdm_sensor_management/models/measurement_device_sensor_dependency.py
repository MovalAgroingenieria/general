# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MeasurementDeviceSensorDependency(models.Model):
    _name = 'mdm.measurement.device.sensor.dependency'
    _description = 'Measurement Device Sensor Dependency'
    _order = 'computed_sensor_id, sequence'

    computed_sensor_id = fields.Many2one(
        comodel_name='mdm.measurement.device.sensor',
        string='Computed Sensor',
        required=True,
        index=True,
        ondelete='cascade',
    )

    dependency_sensor_id = fields.Many2one(
        comodel_name='mdm.measurement.device.sensor',
        string='Dependency Sensor',
        required=True,
        ondelete='restrict',
    )

    variable_name = fields.Char(
        string='Variable Name',
        required=True,
           help='Name used to reference this sensor latest active measurement '
               'value, provided dependency measurement times differ by no '
               'more than three hours, '
             'inside the Custom Python transformation of the computed '
             'sensor (e.g. "temperature").',
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )

    _sql_constraints = [
        ('unique_variable_per_sensor',
         'unique(computed_sensor_id, variable_name)',
         'The variable name must be unique per computed sensor.'),
        ('unique_dependency_per_sensor',
         'unique(computed_sensor_id, dependency_sensor_id)',
         'This sensor is already added as a dependency.'),
    ]

    @api.onchange('dependency_sensor_id')
    def _onchange_dependency_sensor_id(self):
        if not self.dependency_sensor_id:
            return
        siblings = self.computed_sensor_id.dependency_line_ids.filtered(
            lambda line: line.dependency_sensor_id ==
            self.dependency_sensor_id and line != self)
        if siblings:
            self.dependency_sensor_id = False
            return {'warning': {
                'title': _('Duplicate sensor'),
                'message': _('This sensor is already added as a '
                             'dependency.'),
            }}

    @api.constrains('computed_sensor_id', 'dependency_sensor_id')
    def _check_no_self_dependency(self):
        for line in self:
            if line.computed_sensor_id == line.dependency_sensor_id:
                raise ValidationError(
                    _('A sensor cannot depend on itself.'))
