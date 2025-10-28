# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SensorReadingTransformTemplate(models.Model):
    _name = 'mdm.sensor.reading.transform.template'
    _description = 'Sensor Reading Transform Template'
    _order = 'name'

    name = fields.Char(
        string='Name',
        required=True,
        index=True,
    )

    description = fields.Text(
        string='Description',
    )

    readonly = fields.Boolean(
        string='Read Only',
        readonly=True,
        default=False,
        help='Indicates if this template was created by module installation '
             'and should not be deleted',
    )

    target_model_id = fields.Many2one(
        comodel_name='ir.model',
        string='Target Model',
        required=True,
        help='Model where readings will be created',
    )

    target_model = fields.Char(
        string='Target Model Technical Name',
        related='target_model_id.model',
        readonly=True,
    )

    use_all_sensors = fields.Boolean(
        string='Use All Sensors',
        default=False,
        help='If checked, all sensors will be used. Otherwise, only selected '
             'sensors in sensor_ids will be used',
    )

    sensor_ids = fields.Many2many(
        comodel_name='mdm.measurement.device.sensor',
        relation='mdm_sensor_transform_template_sensor_rel',
        column1='template_id',
        column2='sensor_id',
        string='Sensors',
        help='Default sensors for this transformation',
    )

    sensor_domain_filter = fields.Char(
        string='Sensor Domain Filter',
        help='Domain to filter sensors (e.g., [("sensor_type_id.name", '
             '"=", "Temperature")])',
    )

    selection_mode = fields.Selection(
        string='Reading Selection Mode',
        selection=[
            ('date_range', 'Date Range'),
            ('from_date', 'From Date'),
            ('last_reading', 'Last Reading'),
            ('closest_reading', 'Closest Reading'),
        ],
        required=True,
        default='date_range',
    )

    date_from = fields.Datetime(
        string='From Date',
        help='Default from date for transformations',
    )

    date_to = fields.Datetime(
        string='To Date',
        help='Default to date for transformations',
    )

    auto_date_from_last_record = fields.Boolean(
        string='Auto Date From Last Record',
        default=False,
        help='Automatically set date_from based on last record in target '
             'model',
    )

    target_date_field_id = fields.Many2one(
        comodel_name='ir.model.fields',
        string='Target Date Field',
        domain="[('model_id', '=', target_model_id), "
               "('ttype', 'in', ['date', 'datetime'])]",
        help='Date/Datetime field in target model to use for auto date '
             'calculation',
    )

    field_mapping_json = fields.Text(
        string='Field Mapping (JSON)',
        help='JSON mapping from sensor fields to target model fields.\n'
             'Use $field_name to reference reading fields.\n'
             'Use static values directly: "field": "static_value"',
    )

    show_mapping_help = fields.Boolean(
        string='Show Mapping Help',
        default=False,
        help='Display detailed help about field mapping syntax',
    )

    domain_filter = fields.Char(
        string='Domain Filter',
        help='Additional domain to filter readings',
    )

    detect_negative_readings = fields.Boolean(
        string='Detect Negative Readings',
        default=False,
        help='Detect when volume decreases and create in alternative model',
    )

    negative_model_id = fields.Many2one(
        comodel_name='ir.model',
        string='Negative Reading Model',
        help='Model to use when volume decreases '
             '(e.g., wua.negative.flowreading)',
    )

    reference_field = fields.Char(
        string='Reference Field',
        help='Field in target model to identify the meter/device '
             '(e.g., "flowmeter_id")',
    )

    volume_field = fields.Char(
        string='Volume Field',
        default='volume',
        help='Field name that contains the volume value in target model',
    )

    date_field_for_last_reading = fields.Char(
        string='Date Field for Last Reading',
        help='Field name in target model to use for ordering when searching '
             'the last reading (e.g., "reading_time", "measurement_time"). '
             'Used for negative reading detection.',
    )

    negative_field_mapping_json = fields.Text(
        string='Negative Field Mapping (JSON)',
        help='JSON mapping for negative readings. Can use $volume_diff for '
             'the difference between old and new volume',
    )

    active = fields.Boolean(
        string='Active',
        default=True,
    )

    @api.constrains('field_mapping_json')
    def _check_field_mapping_json(self):
        for record in self:
            if record.field_mapping_json:
                try:
                    json.loads(record.field_mapping_json)
                except (ValueError, TypeError) as e:
                    raise UserError(
                        _("Invalid JSON in Field Mapping: %s") % str(e))

    @api.constrains('negative_field_mapping_json')
    def _check_negative_field_mapping_json(self):
        for record in self:
            if record.negative_field_mapping_json:
                try:
                    json.loads(record.negative_field_mapping_json)
                except (ValueError, TypeError) as e:
                    raise UserError(
                        _("Invalid JSON in Negative Field Mapping: %s") %
                        str(e))

    @api.constrains('detect_negative_readings', 'date_field_for_last_reading')
    def _check_negative_reading_config(self):
        for record in self:
            if (record.detect_negative_readings and
                    not record.date_field_for_last_reading):
                raise UserError(
                    _('Date Field for Last Reading is required when '
                      'Detect Negative Readings is enabled'))

    @api.multi
    def unlink(self):
        force_unlink = self.env.context.get('force_unlink', False)
        if not force_unlink:
            for record in self:
                if record.readonly:
                    raise UserError(
                        _("You cannot delete a read-only Transform "
                          "Template."))
        return super(SensorReadingTransformTemplate, self).unlink()
