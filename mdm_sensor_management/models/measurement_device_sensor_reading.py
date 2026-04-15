# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
from datetime import datetime, timedelta
import pytz


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

    def archive_device_sensor_reading(self):
        self.write({'active': False})

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
