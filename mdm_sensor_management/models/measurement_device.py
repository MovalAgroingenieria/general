# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, _


class MeasurementDevice(models.Model):
    _name = 'mdm.measurement.device'
    _description = 'Measurement Device'
    _order = 'name'

    name = fields.Char(
        string='Identifier',
        required=True,
        index=True,
    )

    description = fields.Text(
        string='Description',
    )

    notes = fields.Html(
        string='Notes',
    )

    attributes = fields.Html(
        string='Attributes',
    )

    location = fields.Char(
        string='Location',
    )

    brand = fields.Char(
        string='Brand',
    )

    model = fields.Char(
        string='Model',
    )

    serial_number = fields.Char(
        string='Serial Number',
    )

    installation_date = fields.Date(
        string='Installation Date',
    )

    photo = fields.Binary(
        string='Photo',
        attachment=True,
    )

    category_id = fields.Many2one(
        string='Category',
        comodel_name='mdm.measurement.device.category',
        ondelete='set null',
    )

    sensor_ids = fields.One2many(
        comodel_name='mdm.measurement.device.sensor',
        inverse_name='device_id',
        string='Sensors',
    )

    reading_ids = fields.One2many(
        comodel_name='mdm.measurement.device.sensor.reading',
        inverse_name='device_id',
        string='Readings',
    )

    active = fields.Boolean(
        string='Active',
        default=True,
    )

    _sql_constraints = [
        ('unique_name', 'unique(name)', 'The identifier must be unique.'),
    ]

    def write(self, vals):
        res = super(MeasurementDevice, self).write(vals)
        if 'active' in vals:
            for device in self:
                if not vals['active']:
                    # Archive all sensors of this device
                    device.sensor_ids.write({'active': False})
                else:
                    # Unarchive all sensors of this device
                    sensors = device.with_context(
                        active_test=False).sensor_ids
                    sensors.write({'active': True})
        return res

    def action_view_sensors(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sensors'),
            'res_model': 'mdm.measurement.device.sensor',
            'view_mode': 'tree,form',
            'domain': [('device_id', '=', self.id)],
            'context': {'default_device_id': self.id},
        }

    def action_view_readings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Readings'),
            'res_model': 'mdm.measurement.device.sensor.reading',
            'view_mode': 'tree,form,pivot',
            'domain': [('device_id', '=', self.id)],
            'context': {'default_device_id': self.id},
        }
