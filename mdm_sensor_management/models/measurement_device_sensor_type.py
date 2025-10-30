# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError


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

    _sql_constraints = [
        ('unique_name', 'unique(name)', 'The sensor type must be unique.'),
    ]

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
