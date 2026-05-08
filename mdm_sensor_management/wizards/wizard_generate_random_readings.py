# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import random
import logging
from datetime import timedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class WizardGenerateRandomReadings(models.TransientModel):
    _name = 'mdm.wizard.generate.random.readings'
    _description = 'Generate Random Sensor Readings'

    sensor_ids = fields.Many2many(
        comodel_name='mdm.measurement.device.sensor',
        relation='mdm_wizard_gen_random_readings_sensor_rel',
        column1='wizard_id',
        column2='sensor_id',
        string='Sensors',
        required=True,
    )

    date_from = fields.Datetime(
        string='Start Date',
        required=True,
    )

    date_to = fields.Datetime(
        string='End Date',
        required=True,
    )

    interval_minutes = fields.Integer(
        string='Interval (minutes)',
        required=True,
        default=60,
    )

    value_min = fields.Float(
        string='Min Value',
        required=True,
        digits=(32, 4),
        default=0.0,
    )

    value_max = fields.Float(
        string='Max Value',
        required=True,
        digits=(32, 4),
        default=100.0,
    )

    state = fields.Selection(
        string='State',
        selection=[
            ('draft', 'Draft'),
            ('done', 'Done'),
        ],
        default='draft',
        readonly=True,
    )

    result_message = fields.Text(
        string='Result',
        readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super(WizardGenerateRandomReadings, self).default_get(
            fields_list)
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            res['sensor_ids'] = [(6, 0, active_ids)]
        return res

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from and wizard.date_to:
                if wizard.date_to <= wizard.date_from:
                    raise UserError(
                        _("End Date must be later than Start Date."))

    @api.constrains('interval_minutes')
    def _check_interval(self):
        for wizard in self:
            if wizard.interval_minutes < 1:
                raise UserError(
                    _("Interval must be at least 1 minute."))

    @api.constrains('value_min', 'value_max')
    def _check_values(self):
        for wizard in self:
            if wizard.value_max < wizard.value_min:
                raise UserError(
                    _("Max Value must be greater than or equal to Min Value."))

    @api.multi
    def action_generate(self):
        self.ensure_one()
        reading_model = self.env['mdm.measurement.device.sensor.reading']
        date_from = fields.Datetime.from_string(self.date_from)
        date_to = fields.Datetime.from_string(self.date_to)
        interval = timedelta(minutes=self.interval_minutes)
        value_min = self.value_min
        value_max = self.value_max
        created_count = 0
        skipped_count = 0

        for sensor in self.sensor_ids:
            current = date_from
            while current <= date_to:
                value = random.uniform(value_min, value_max)
                time_str = fields.Datetime.to_string(current)
                try:
                    with self.env.cr.savepoint():
                        reading_model.create({
                            'sensor_id': sensor.id,
                            'measurement_time': time_str,
                            'value': value,
                        })
                        created_count += 1
                except Exception as e:
                    _logger.warning(
                        'Skipped reading for sensor %s at %s: %s',
                        sensor.name, time_str, e)
                    skipped_count += 1
                current += interval

        message = _("%d readings created.") % created_count
        if skipped_count:
            message += '\n' + _("%d skipped (duplicates or errors).") % (
                skipped_count)

        self.write({'state': 'done', 'result_message': message})
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }
