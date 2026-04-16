# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


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

    def write(self, vals):
        res = super(MeasurementDeviceSensor, self).write(vals)
        if 'active' in vals:
            for sensor in self:
                if not vals['active']:
                    # Archive all readings of this sensor
                    sensor.sensor_readings.write({'active': False})
                else:
                    # Unarchive all readings of this sensor
                    readings = sensor.with_context(
                        active_test=False).sensor_readings
                    readings.write({'active': True})
        return res

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
