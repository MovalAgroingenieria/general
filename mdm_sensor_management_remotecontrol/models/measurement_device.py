# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
from odoo import models, fields, api


class MeasurementDevice(models.Model):
    _inherit = 'mdm.measurement.device'

    remotecontrol_id = fields.Many2one(
        string='Remotecontrol',
        comodel_name='remotecontrol',
    )

    remotecontrol_params = fields.Text(
        string='Remotecontrol Parameters',
    )

    remotecontrol_params_valid = fields.Boolean(
        string='Valid JSON Parameters',
        compute='_compute_remotecontrol_params_valid',
        store=True,
    )

    readings_procedure_id = fields.Many2one(
        string='Readings Procedure',
        comodel_name='remotecontrol.procedure',
        store=False,
        compute='_compute_readings_procedure_id',
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

    @api.multi
    def _compute_readings_procedure_id(self):
        for record in self:
            resp = None
            procedures = self.env['remotecontrol.procedure'].search(
                [('remote_id', '=', record.remotecontrol_id.id),
                 ('procedure_for_readings', '=', True)])
            if procedures and len(procedures) == 1:
                resp = procedures[0].id
            record.readings_procedure_id = resp

    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        existing_records = self.with_context(active_test=False).search(
            [('name', 'like', self.name + '%')])
        number_of_existing_records = 0
        if existing_records:
            number_of_existing_records = len(existing_records)
        number_of_existing_records = number_of_existing_records + 1
        default['name'] = \
            self.name + ' (' + str(number_of_existing_records) + ')'
        if self.sensor_ids:
            sensor_vals = []
            for sensor in self.sensor_ids:
                sensor_vals.append((0, 0, {
                    'name': sensor.name,
                    'description': sensor.description,
                    'type_id': sensor.type_id.id,
                    'remotecontrol_params': sensor.remotecontrol_params,
                }))
            default['sensor_ids'] = sensor_vals
        return super(MeasurementDevice, self).copy(default)

    @api.multi
    def action_run_readings_procedure(self):
        self.ensure_one()
        procedure = self.readings_procedure_id
        if not procedure:
            return
        # Pass device_ids via context so it can be injected into the bag
        procedure.with_context(
            selected_device_ids=self.ids,
        ).run()
