# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class MeasurementDeviceSensorReading(models.Model):
    _inherit = 'mdm.measurement.device.sensor.reading'

    remotecontrol_origin_id = fields.Many2one(
        comodel_name='remotecontrol',
        string='Remotecontrol Origin',
        readonly=True,
    )
