# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import math
from datetime import datetime, timedelta
import pytz
from simpleeval import simple_eval

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
_logger = logging.getLogger(__name__)


class MeasurementDeviceSensorReading(models.Model):
    _name = 'mdm.measurement.device.sensor.reading'
    _description = 'Measurement Device Sensor Reading'
    _order = 'sensor_id, measurement_time desc'

    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True,
        index=True,
    )

    device_id = fields.Many2one(
        string='Measurement Device',
        comodel_name='mdm.measurement.device',
        compute='_compute_device_id',
        store=True,
        index=True,
        ondelete='restrict',
    )

    sensor_id = fields.Many2one(
        comodel_name='mdm.measurement.device.sensor',
        string='Sensor',
        required=True,
        index=True,
        ondelete='restrict',
    )

    measurement_time = fields.Datetime(
        string='Measurement Time',
        required=True,
    )

    value = fields.Float(
        string='Value',
        required=True,
        digits=(32, 4),
    )

    uom_id = fields.Many2one(
        comodel_name='mdm.measurement.device.sensor.uom',
        string='Unit of Measure',
        related='sensor_id.uom_id',
        store=True,
        readonly=True,
    )

    type_id = fields.Many2one(
        comodel_name='mdm.measurement.device.sensor.type',
        string='Sensor Type',
        related='sensor_id.type_id',
        store=True,
        readonly=True,
    )

    raw_value = fields.Float(
        string='Raw Value',
        digits=(32, 4),
        readonly=True,
        help='Original value before applying the measurement transformation.',
    )

    measurement_transformation_type = fields.Selection(
        selection=[
            ('arithmetic', 'Arithmetic Expression'),
            ('custom_python', 'Custom Python'),
        ],
        string='Transformation Type Applied',
        readonly=True,
    )

    measurement_transformation = fields.Char(
        string='Transformation Applied',
        readonly=True,
        help='Formula that was applied to convert raw_value into value.',
    )

    is_out_of_range = fields.Boolean(
        string='Out of range',
        store=True,
        index=True,
        compute='_compute_is_out_of_range',
        help='True if the reading value falls outside the effective '
             'min/max range defined for the sensor.',
    )

    range_status = fields.Selection(
        string='Range status',
        selection=[
            ('normal', 'Normal'),
            ('low', 'Below minimum'),
            ('high', 'Above maximum'),
            ('unchecked', 'Not checked'),
        ],
        store=True,
        index=True,
        compute='_compute_is_out_of_range',
        help='Validity status of the reading with respect to the sensor '
             'range: normal, below minimum, above maximum, or not checked '
             '(when range validation is disabled for the sensor).',
    )

    active = fields.Boolean(
        string='Active',
        default=True,
    )

    measurement_date_madrid = fields.Date(
        string='Date (Europe/Madrid)',
        compute='_compute_measurement_dates',
        store=True,
        index=True,
        help='Date in Europe/Madrid timezone',
    )

    is_last_sensor_reading = fields.Boolean(
        string='Last Reading',
        compute='_compute_is_last_sensor_reading',
        search='_search_is_last_sensor_reading',
    )

    _sql_constraints = [
        ('unique_name', 'unique(name)', 'The sensor reading must be unique.'),
    ]

    @api.depends('measurement_time')
    def _compute_measurement_dates(self):
        madrid_tz = pytz.timezone('Europe/Madrid')
        for record in self:
            if record.measurement_time:
                dt_utc = fields.Datetime.from_string(record.measurement_time)
                dt_utc_aware = pytz.UTC.localize(dt_utc)
                dt_madrid = dt_utc_aware.astimezone(madrid_tz)
                record.measurement_date_madrid = dt_madrid.strftime('%Y-%m-%d')
            else:
                record.measurement_date_madrid = False

    @api.depends('device_id.name', 'sensor_id.name', 'measurement_time')
    def _compute_name(self):
        for record in self:
            name = ''
            if (record.device_id and record.sensor_id and
                    record.measurement_time):
                name = '%s - %s - %s' % (
                    record.device_id.name,
                    record.sensor_id.name,
                    record.measurement_time)
            record.name = name

    @api.depends('sensor_id')
    def _compute_device_id(self):
        for record in self:
            device_id = None
            if record.sensor_id and record.sensor_id.device_id:
                device_id = record.sensor_id.device_id
            record.device_id = device_id

    @api.multi
    @api.depends('value', 'sensor_id')
    def _compute_is_out_of_range(self):
        for record in self:
            if not record.sensor_id.effective_has_validation:
                record.range_status = 'unchecked'
                record.is_out_of_range = False
            elif record.value < record.sensor_id.effective_min_value:
                record.range_status = 'low'
                record.is_out_of_range = True
            elif record.value > record.sensor_id.effective_max_value:
                record.range_status = 'high'
                record.is_out_of_range = True
            else:
                record.range_status = 'normal'
                record.is_out_of_range = False

    def archive_device_sensor_reading(self):
        self.write({'active': False})

    @api.model
    def create(self, vals):
        vals = self._apply_measurement_transformation(vals)
        return super(MeasurementDeviceSensorReading, self).create(vals)

    @api.multi
    def write(self, vals):
        if 'value' in vals and 'raw_value' not in vals:
            for record in self:
                record_vals = dict(vals)
                record_vals = self._apply_measurement_transformation(
                    record_vals,
                    sensor=record.sensor_id)
                super(MeasurementDeviceSensorReading, record).write(
                    record_vals)
            return True
        return super(MeasurementDeviceSensorReading, self).write(vals)

    @api.model
    def _apply_measurement_transformation(self, vals, sensor=None):
        if sensor is None:
            sensor_id = vals.get('sensor_id')
            if sensor_id:
                sensor = self.env[
                    'mdm.measurement.device.sensor'].browse(sensor_id)
        if not sensor:
            return vals
        transformation_type = sensor.measurement_transformation_type or \
            'arithmetic'
        if transformation_type == 'arithmetic':
            transformation = sensor.measurement_transformation or '$'
        else:
            transformation = sensor.measurement_transformation_python or ''
        raw_value = vals.get('value', 0.0)
        vals['raw_value'] = raw_value
        vals['measurement_transformation_type'] = transformation_type
        vals['measurement_transformation'] = transformation
        vals['value'] = self._transform_value(
            raw_value, transformation, transformation_type)
        return vals

    @api.model
    def _transform_value(self, value, transformation,
                         transformation_type='arithmetic'):
        allowed_functions = {
            'sqrt': math.sqrt,
            'pow': pow,
            'log': math.log,
            'log10': math.log10,
            'exp': math.exp,
            'abs': abs,
            'round': round,
            'ceil': math.ceil,
            'floor': math.floor,
            'min': min,
            'max': max,
        }
        try:
            if transformation_type == 'arithmetic':
                expression = transformation.replace('$', str(value))
                result = simple_eval(
                    expression, functions=allowed_functions)
                return float(result)
            if transformation_type == 'custom_python':
                if not transformation or not transformation.strip():
                    raise UserError(
                        _('Custom Python transformation is empty.'))
                localdict = {
                    'value': float(value),
                    'result': None,
                    'math': math,
                    'sqrt': math.sqrt,
                    'pow': pow,
                    'log': math.log,
                    'log10': math.log10,
                    'exp': math.exp,
                    'abs': abs,
                    'round': round,
                    'ceil': math.ceil,
                    'floor': math.floor,
                    'min': min,
                    'max': max,
                }
                safe_eval(
                    transformation,
                    localdict,
                    mode='exec',
                    nocopy=True,
                )
                if localdict.get('result') is None:
                    raise UserError(
                        _('The custom Python transformation must '
                          'assign a value to "result".'))
                return float(localdict['result'])
            raise UserError(
                _('Unknown transformation type: %s') %
                transformation_type)
        except UserError:
            raise
        except Exception as e:
            _logger.warning(
                'Transformation error: %s (type=%s, formula=%s, value=%s)',
                e, transformation_type, transformation, value)
            raise UserError(
                _('Error applying transformation "%s" to value %s: %s') %
                (transformation, value, e))

    @api.model
    def cron_cleanup_old_readings(self):
        # Search for sensors with a positive retention period
        sensors = self.env['mdm.measurement.device.sensor'].search([
            ('reading_retention_days', '>', 0),
        ])
        for sensor in sensors:
            cutoff_datetime = datetime.now() - timedelta(
                days=sensor.reading_retention_days)
            cutoff_date_str = cutoff_datetime.strftime('%Y-%m-%d %H:%M:%S')
            old_readings = self.search([
                ('sensor_id', '=', sensor.id),
                ('measurement_time', '<', cutoff_date_str),
            ])
            if old_readings:
                old_readings.write({'active': False})
        return True

    @api.multi
    def _compute_is_last_sensor_reading(self):
        # Batch: prefetch sensor_id and last_measurement
        sensors = self.mapped('sensor_id')
        if sensors:
            sensors.mapped('last_measurement')
        for record in self:
            is_last_reading = False
            if record.sensor_id and record.sensor_id.last_measurement:
                is_last_reading = (
                    record.id == record.sensor_id.last_measurement.id)
            record.is_last_sensor_reading = is_last_reading

    def _search_is_last_sensor_reading(self, operator, value):
        domain = [('id', '=', 0)]
        sql_query = """
            SELECT DISTINCT ON (sensor_id) id
            FROM mdm_measurement_device_sensor_reading
            WHERE active = TRUE
            ORDER BY sensor_id, measurement_time DESC
        """
        self.env.cr.execute(sql_query)
        result = [rec[0] for rec in self.env.cr.fetchall()]
        if operator == '=' and value:
            domain = [('id', 'in', result)]
        elif operator == '=' and not value:
            domain = [('id', 'not in', result)]
        elif operator == '!=' and value:
            domain = [('id', 'not in', result)]
        elif operator == '!=' and not value:
            domain = [('id', 'in', result)]
        return domain
