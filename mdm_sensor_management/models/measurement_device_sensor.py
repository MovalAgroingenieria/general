# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models, fields, _


class MeasurementDeviceSensor(models.Model):
    _name = 'mdm.measurement.device.sensor'
    _description = 'Measurement Device Sensor'
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
             "Older readings should be cleaned up automatically by cron."
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
