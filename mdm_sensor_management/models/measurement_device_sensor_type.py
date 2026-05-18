# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MeasurementDeviceSensorType(models.Model):
    _name = 'mdm.measurement.device.sensor.type'
    _description = 'Sensor Type'
    _order = 'name'

    name = fields.Char(
        string='Name',
        required=True,
        index=True,
        translate=True,
    )
    description = fields.Text(
        string='Description',
    )

    readonly = fields.Boolean(
        string='Read Only',
        readonly=True,
        default=False,
        help='Indicates if this sensor type was created by module '
             'installation and should not be deleted',
    )

    uom_id = fields.Many2one(
        comodel_name='mdm.measurement.device.sensor.uom',
        string='Unit of Measure',
        required=True,
        ondelete='restrict',
    )

    sensor_ids = fields.One2many(
        comodel_name='mdm.measurement.device.sensor',
        inverse_name='type_id',
        string='Sensors',
    )

    has_range_validation = fields.Boolean(
        string='Range validation',
        default=False,
        index=True,
        help='If enabled, readings of sensors of this type will be checked '
             'against the defined min/max values.',
    )

    min_value = fields.Float(
        string='Minimum value',
        digits=(32, 4),
        help='Lower bound for normal readings. Readings below this value '
             'will be flagged as out of range.',
    )

    max_value = fields.Float(
        string='Maximum value',
        digits=(32, 4),
        help='Upper bound for normal readings. Readings above this value '
             'will be flagged as out of range.',
    )

    _sql_constraints = [
        ('unique_name', 'unique(name)', 'The sensor type must be unique.'),
    ]

    @api.onchange('has_range_validation')
    def _onchange_has_range_validation(self):
        if not self.has_range_validation:
            self.min_value = 0.0
            self.max_value = 0.0

    @api.multi
    def write(self, vals):
        range_fields_changed = bool(
            {'has_range_validation', 'min_value', 'max_value'} & set(vals),
        )
        disabling = 'has_range_validation' in vals and not vals[
            'has_range_validation']
        if disabling:
            vals['min_value'] = 0.0
            vals['max_value'] = 0.0
        res = super(MeasurementDeviceSensorType, self).write(vals)
        if range_fields_changed:
            for record in self:
                _logger.info(
                    'write: range fields changed on type %s (%s), '
                    'triggering reading recompute', record.id, record.name,
                )
                record.action_recompute_readings_range_status()
        return res

    @api.multi
    def action_recompute_readings_range_status(self):
        self.ensure_one()
        Reading = self.env['mdm.measurement.device.sensor.reading']
        readings = Reading.search(
            [('sensor_id.type_id', '=', self.id)],
        )
        if not readings:
            return
        _logger.info(
            'action_recompute_readings_range_status: processing %d readings '
            'for sensor type %s (%s)', len(readings), self.id, self.name,
        )
        ids_normal = []
        ids_low = []
        ids_high = []
        ids_unchecked = []
        sensor_cache = {}
        for record in readings:
            sid = record.sensor_id.id
            if sid not in sensor_cache:
                sensor_cache[sid] = {
                    'has_validation':
                    record.sensor_id.effective_has_validation,
                    'min_value': record.sensor_id.effective_min_value,
                    'max_value': record.sensor_id.effective_max_value,
                }
            sc = sensor_cache[sid]
            if not sc['has_validation']:
                ids_unchecked.append(record.id)
            elif record.value < sc['min_value']:
                ids_low.append(record.id)
            elif record.value > sc['max_value']:
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
            'action_recompute_readings_range_status: done. '
            'normal=%d low=%d high=%d unchecked=%d',
            len(ids_normal), len(ids_low), len(ids_high), len(ids_unchecked),
        )

    @api.multi
    def unlink(self):
        force_unlink = self.env.context.get('force_unlink', False)
        if not force_unlink:
            for record in self:
                if record.readonly:
                    raise UserError(
                        _("You cannot delete a read-only Sensor Type."))
        return super(MeasurementDeviceSensorType, self).unlink()

    def action_view_sensors(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sensors'),
            'res_model': 'mdm.measurement.device.sensor',
            'view_mode': 'tree,form',
            'domain': [('type_id', '=', self.id)],
            'context': {'default_type_id': self.id},
        }
