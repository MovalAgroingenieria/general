# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.translate import _


class MeasurementDeviceSensorUOM(models.Model):
    _name = 'mdm.measurement.device.sensor.uom'
    _description = 'Sensor Unit of Measure'
    _order = 'name'

    name = fields.Char(
        string='Name',
        required=True,
        index=True,
    )

    short_name = fields.Char(
        string='Short Name',
        index=True,
    )

    description = fields.Char(
        string='Description',
    )

    notes = fields.Html(
        string='Notes',
    )

    readonly = fields.Boolean(
        string='Read Only',
        readonly=True,
        default=False,
        help='Indicates if this UOM was created by module installation '
             'and should not be deleted',
    )

    sensor_ids = fields.One2many(
        comodel_name='mdm.measurement.device.sensor',
        inverse_name='uom_id',
        string='Sensors',
    )

    _sql_constraints = [
        ('unique_name', 'unique(name)', 'The unit of measure must be unique.'),
        ('unique_short_name', 'unique(short_name)',
         'The short name must be unique.'),
    ]

    @api.multi
    def unlink(self):
        force_unlink = self.env.context.get('force_unlink', False)
        if not force_unlink:
            for record in self:
                if record.readonly:
                    raise UserError(
                        _("You cannot delete a read-only Unit of Measure."))
        return super(MeasurementDeviceSensorUOM, self).unlink()

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            if record.short_name:
                display_name = "%s (%s)" % (record.name, record.short_name)
            else:
                display_name = record.name
            result.append((record.id, display_name))
        return result
