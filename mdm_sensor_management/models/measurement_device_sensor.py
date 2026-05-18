# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class MeasurementDeviceSensor(models.Model):
    _name = 'mdm.measurement.device.sensor'
    _description = 'Measurement Device Sensor'
    _order = 'name'

    name = fields.Char(
        string='Name',
        required=True,
        index=True,
        translate=False,
    )

    description = fields.Text(
        string='Description',
    )

    device_id = fields.Many2one(
        comodel_name='mdm.measurement.device',
        string='Measurement Device',
        required=True,
        index=True,
        ondelete='cascade',
    )

    type_id = fields.Many2one(
        comodel_name='mdm.measurement.device.sensor.type',
        string='Sensor Type',
        required=True,
        ondelete='restrict',
    )

    sensor_readings = fields.One2many(
        comodel_name='mdm.measurement.device.sensor.reading',
        inverse_name='sensor_id',
        string='Readings',
    )

    uom_id = fields.Many2one(
        comodel_name='mdm.measurement.device.sensor.uom',
        string='Unit of Measure',
        related='type_id.uom_id',
        store=True,
        readonly=True,
    )

    reading_retention_days = fields.Integer(
        string="Retention (days)",
        default=-1,
        help="Maximum number of days to keep readings linked to this device. "
             "Older readings should be cleaned up automatically by cron.",
    )

    measurement_transformation_type = fields.Selection(
        selection=[
            ('arithmetic', 'Arithmetic Expression'),
            ('custom_python', 'Custom Python'),
        ],
        string='Transformation Type',
        required=True,
        default='arithmetic',
    )

    measurement_transformation = fields.Char(
        string='Arithmetic Transformation',
        default='$',
        help='Formula to transform the raw measurement value before storing.'
             ' Use $ as placeholder for the original raw value.\n'
             'Available functions: sqrt, pow, log, log10, exp, abs, round,'
             ' ceil, floor, min, max.\n'
             'Examples: $ * 0.001 | sqrt($) | pow($, 2) | log10($)',
    )

    measurement_transformation_python = fields.Text(
        string='Custom Python Transformation',
        groups='base.group_system',
        help='Custom Python code to transform the raw measurement value.\n'
             'The raw value is available as variable "value".\n'
             'The final transformed value must be assigned to "result".\n\n'
             'Available: math, sqrt, pow, log, log10, exp, abs, round,'
             ' ceil, floor, min, max.\n\n'
             'Example:\n'
             '  pct = float(value)\n'
             '  result = pct * 100',
    )

    has_range_validation = fields.Boolean(
        string='Range validation',
        default=False,
        help='If enabled, this sensor validates readings against a '
             'min/max range regardless of the sensor type setting.',
    )

    has_custom_range = fields.Boolean(
        string='Custom range',
        default=False,
        help='If enabled, this sensor uses its own min/max values instead '
             'of those defined at the sensor type level.',
    )

    custom_min_value = fields.Float(
        string='Custom minimum value',
        digits=(32, 4),
        help='Lower bound specific to this sensor. Only applies when '
             'custom range is enabled.',
    )

    custom_max_value = fields.Float(
        string='Custom maximum value',
        digits=(32, 4),
        help='Upper bound specific to this sensor. Only applies when '
             'custom range is enabled.',
    )

    effective_has_validation = fields.Boolean(
        string='Effective validation',
        store=True,
        compute='_compute_effective_range',
        readonly=True,
        help='Resolved validation flag: True if this sensor or its type '
             'has range validation enabled.',
    )

    effective_min_value = fields.Float(
        string='Effective minimum',
        digits=(32, 4),
        store=True,
        compute='_compute_effective_range',
        readonly=True,
        help='Resolved minimum value: custom range if enabled, otherwise '
             'the sensor type minimum.',
    )

    effective_max_value = fields.Float(
        string='Effective maximum',
        digits=(32, 4),
        store=True,
        compute='_compute_effective_range',
        readonly=True,
        help='Resolved maximum value: custom range if enabled, otherwise '
             'the sensor type maximum.',
    )

    active = fields.Boolean(
        string='Active',
        default=True,
    )

    last_measurement = fields.Many2one(
        comodel_name='mdm.measurement.device.sensor.reading',
        string="Last measurement",
        compute="_compute_last_measurement",
    )

    last_measurement_time = fields.Datetime(
        string="Last measurement time",
        compute='_compute_last_measurement',
        search='_search_last_measurement_time',
    )

    last_measurement_value = fields.Float(
        string="Last measurement value",
        digits=(32, 2),
        compute="_compute_last_measurement")

    @api.constrains('name', 'device_id')
    def _check_unique_sensor_per_device(self):
        for sensor in self:
            if sensor.device_id and sensor.name:
                duplicate = self.search([
                    ('id', '!=', sensor.id),
                    ('device_id', '=', sensor.device_id.id),
                    ('name', '=', sensor.name),
                ], limit=1)
                if duplicate:
                    raise ValidationError(
                        _("A sensor with name '%s' already exists for "
                          "device '%s'.\nPlease use a different name or "
                          "check for duplicates.") % (
                            sensor.name, sensor.device_id.name))

    @api.onchange('has_range_validation')
    def _onchange_has_range_validation(self):
        if self.has_range_validation:
            self.has_custom_range = True

    @api.onchange('has_custom_range')
    def _onchange_has_custom_range(self):
        if not self.has_custom_range:
            self.custom_min_value = 0.0
            self.custom_max_value = 0.0

    def write(self, vals):
        res = super(MeasurementDeviceSensor, self).write(vals)
        if 'active' in vals:
            for sensor in self:
                if not vals['active']:
                    sensor.sensor_readings.write({'active': False})
                else:
                    readings = sensor.with_context(
                        active_test=False).sensor_readings
                    readings.write({'active': True})
        sensor_range_fields = {
            'has_range_validation', 'has_custom_range',
            'custom_min_value', 'custom_max_value',
        }
        if bool(sensor_range_fields & set(vals)):
            for record in self:
                record.action_recompute_sensor_readings_range_status()
        return res

    @api.multi
    def action_recompute_sensor_readings_range_status(self):
        self.ensure_one()
        Reading = self.env['mdm.measurement.device.sensor.reading']
        readings = Reading.search([('sensor_id', '=', self.id)])
        if not readings:
            return
        _logger.info(
            'action_recompute_sensor_readings_range_status: processing %d '
            'readings for sensor %s (%s)',
            len(readings), self.id, self.name,
        )
        ids_normal = []
        ids_low = []
        ids_high = []
        ids_unchecked = []
        has_validation = self.effective_has_validation
        min_value = self.effective_min_value
        max_value = self.effective_max_value
        for record in readings:
            if not has_validation:
                ids_unchecked.append(record.id)
            elif record.value < min_value:
                ids_low.append(record.id)
            elif record.value > max_value:
                ids_high.append(record.id)
            else:
                ids_normal.append(record.id)
        cr = self.env.cr
        if ids_normal:
            cr.execute(
                "UPDATE mdm_measurement_device_sensor_reading "
                "SET range_status = 'normal', is_out_of_range = false "
                "WHERE id = ANY(%s)",
                (ids_normal,),
            )
        if ids_low:
            cr.execute(
                "UPDATE mdm_measurement_device_sensor_reading "
                "SET range_status = 'low', is_out_of_range = true "
                "WHERE id = ANY(%s)",
                (ids_low,),
            )
        if ids_high:
            cr.execute(
                "UPDATE mdm_measurement_device_sensor_reading "
                "SET range_status = 'high', is_out_of_range = true "
                "WHERE id = ANY(%s)",
                (ids_high,),
            )
        if ids_unchecked:
            cr.execute(
                "UPDATE mdm_measurement_device_sensor_reading "
                "SET range_status = 'unchecked', is_out_of_range = false "
                "WHERE id = ANY(%s)",
                (ids_unchecked,),
            )
        readings.invalidate_cache(
            ['is_out_of_range', 'range_status'], readings.ids,
        )
        _logger.info(
            'action_recompute_sensor_readings_range_status: done. '
            'normal=%d low=%d high=%d unchecked=%d',
            len(ids_normal), len(ids_low), len(ids_high), len(ids_unchecked),
        )

    @api.multi
    @api.depends(
        'has_range_validation',
        'has_custom_range',
        'custom_min_value',
        'custom_max_value',
        'type_id.has_range_validation',
        'type_id.min_value',
        'type_id.max_value',
    )
    def _compute_effective_range(self):
        for record in self:
            effective_has_validation = (
                record.has_range_validation or
                record.type_id.has_range_validation
            )
            if record.has_custom_range:
                effective_min_value = record.custom_min_value
                effective_max_value = record.custom_max_value
            else:
                effective_min_value = record.type_id.min_value
                effective_max_value = record.type_id.max_value
            record.effective_has_validation = effective_has_validation
            record.effective_min_value = effective_min_value
            record.effective_max_value = effective_max_value

    @api.multi
    def _compute_last_measurement(self):
        for record in self:
            self.env.cr.execute("""
                SELECT id, measurement_time, value
                FROM mdm_measurement_device_sensor_reading
                WHERE sensor_id = %s AND active = TRUE
                ORDER BY measurement_time DESC
                LIMIT 1
            """, (record.id,))
            result = self.env.cr.fetchone()
            if result:
                record.last_measurement = result[0]
                record.last_measurement_time = result[1]
                record.last_measurement_value = result[2]
            else:
                record.last_measurement = False
                record.last_measurement_time = False
                record.last_measurement_value = 0.0

    def _search_last_measurement_time(self, operator, value):
        if operator in (">=", ">"):
            return [("date_to", operator, value)]
        elif operator in ("<=", "<"):
            return [("date_from", operator, value)]
        raise UserError(
            _("Unsupported operator %s for searching on date") % (operator,),
        )

    def action_view_readings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sensor Readings'),
            'res_model': 'mdm.measurement.device.sensor.reading',
            'view_mode': 'tree,form,pivot',
            'domain': [('sensor_id', '=', self.id)],
            'context': {'default_sensor_id': self.id},
        }
