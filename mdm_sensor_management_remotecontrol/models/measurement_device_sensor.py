# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
from odoo import models, fields, api


class MeasurementDeviceSensor(models.Model):
    _inherit = 'mdm.measurement.device.sensor'

    remotecontrol_id = fields.Many2one(
        string='Remotecontrol',
        comodel_name='remotecontrol',
        related='device_id.remotecontrol_id',
        store=True,
        readonly=True,
    )

    remotecontrol_params = fields.Text(
        string='Remotecontrol Parameters',
    )

    remotecontrol_params_valid = fields.Boolean(
        string='Valid JSON Parameters',
        compute='_compute_remotecontrol_params_valid',
        store=True,
    )

    @api.depends('remotecontrol_params')
    def _compute_remotecontrol_params_valid(self):
        for record in self:
            remotecontrol_params_valid = True
            if record.remotecontrol_params:
                try:
                    json.loads(record.remotecontrol_params)
                    remotecontrol_params_valid = True
                except (ValueError, TypeError):
                    remotecontrol_params_valid = False
            record.remotecontrol_params_valid = remotecontrol_params_valid
