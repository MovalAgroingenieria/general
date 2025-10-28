# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, exceptions, _
from odoo.tools.safe_eval import safe_eval
from dateutil.relativedelta import relativedelta
import logging
import json
import re

_logger = logging.getLogger(__name__)


class SensorReadingTransformWizard(models.TransientModel):
    _name = 'mdm.sensor.reading.transform.wizard'
    _description = 'Transform Sensor Readings to Target Model'

    template_id = fields.Many2one(
        comodel_name='mdm.sensor.reading.transform.template',
        string='Template',
        help='Select a template to load configuration',
    )

    name = fields.Char(
        string='Template Name',
        help='Name for this transformation (used when saving as template)',
    )

    use_all_sensors = fields.Boolean(
        string='Use All Sensors',
        default=False,
        help='If checked, all sensors will be used. Otherwise, only selected '
             'sensors in sensor_ids will be used',
    )

    sensor_ids = fields.Many2many(
        comodel_name='mdm.measurement.device.sensor',
        relation='mdm_sensor_transform_wizard_sensor_rel',
        column1='wizard_id',
        column2='sensor_id',
        string='Sensors',
        help='Sensors whose readings will be transformed',
    )

    sensor_domain_filter = fields.Char(
        string='Sensor Domain Filter',
        help='Domain to filter readings (e.g., [("sensor_type_id.name", '
             '"=", "Temperature")]). This filter is always applied.',
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
        help='Method to select which readings to transform',
    )

    date_from = fields.Datetime(
        string='From Date',
        help='Start date for date_range or from_date modes',
    )

    date_to = fields.Datetime(
        string='To Date',
        help='End date for date_range mode',
    )

    reference_date = fields.Datetime(
        string='Reference Date',
        help='Reference date for closest_reading mode',
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

    target_date_field = fields.Char(
        string='Target Date Field Name',
        related='target_date_field_id.name',
        readonly=True,
        store=False,
    )

    date_from_computed = fields.Datetime(
        string='Computed From Date',
        compute='_compute_date_from_computed',
        store=False,
        help='Automatically computed date based on last record',
    )

    field_mapping_json = fields.Text(
        string='Field Mapping (JSON)',
        required=True,
        help='JSON mapping from sensor fields to target model fields.\n'
             'Use $field_name to reference reading fields.\n'
             'Use static values directly: "field": "static_value".\n'
             'Example: {"reading_time": "$measurement_time", '
             '"volume": "$value * 3.6", "active": true, '
             '"notes": "Imported from sensor"}',
    )

    show_mapping_help = fields.Boolean(
        string='Show Mapping Help',
        default=False,
        help='Display detailed help about field mapping syntax',
    )

    domain_filter = fields.Char(
        string='Domain Filter',
        help='Additional domain to filter readings (Python expression)',
    )

    # Negative reading detection fields
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

    negative_model = fields.Char(
        string='Negative Model Technical Name',
        related='negative_model_id.model',
        readonly=True,
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

    @api.constrains('detect_negative_readings', 'date_field_for_last_reading')
    def _check_negative_reading_config(self):
        """Validate negative reading configuration."""
        for record in self:
            if (record.detect_negative_readings and
                    not record.date_field_for_last_reading):
                raise exceptions.ValidationError(
                    _('Date Field for Last Reading is required when '
                      'Detect Negative Readings is enabled'))

    @api.depends('auto_date_from_last_record', 'target_model_id',
                 'target_date_field_id')
    def _compute_date_from_computed(self):
        for record in self:
            if (record.auto_date_from_last_record and
                    record.target_model_id and record.target_date_field_id):
                try:
                    target_model = self.env[record.target_model_id.model]
                    field_name = record.target_date_field_id.name
                    # Search for the last record ordered by the date field
                    last_record = target_model.search(
                        [],
                        order='%s desc' % field_name,
                        limit=1,
                    )
                    if last_record:
                        date_value = getattr(last_record, field_name, False)
                        if date_value:
                            record.date_from_computed = date_value
                        else:
                            record.date_from_computed = False
                    else:
                        record.date_from_computed = False
                except Exception as e:
                    _logger.warning(
                        'Error computing auto date from last record: %s',
                        str(e))
                    record.date_from_computed = False
            else:
                record.date_from_computed = False

    @api.onchange('auto_date_from_last_record', 'date_from_computed')
    def _onchange_auto_date_from_last_record(self):
        if self.auto_date_from_last_record and self.date_from_computed:
            self.date_from = self.date_from_computed

    @api.onchange('target_model_id')
    def _onchange_target_model_id(self):
        # Reset auto date fields when target model changes
        self.auto_date_from_last_record = False
        self.target_date_field_id = False

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id:
            # Populate all fields from template
            self.name = self.template_id.name
            self.use_all_sensors = self.template_id.use_all_sensors
            self.sensor_ids = self.template_id.sensor_ids
            self.sensor_domain_filter = self.template_id.sensor_domain_filter
            self.target_model_id = self.template_id.target_model_id
            self.selection_mode = self.template_id.selection_mode
            self.date_from = self.template_id.date_from
            self.date_to = self.template_id.date_to
            self.auto_date_from_last_record = \
                self.template_id.auto_date_from_last_record
            self.target_date_field_id = self.template_id.target_date_field_id
            self.field_mapping_json = self.template_id.field_mapping_json
            self.domain_filter = self.template_id.domain_filter
            self.detect_negative_readings = \
                self.template_id.detect_negative_readings
            self.negative_model_id = self.template_id.negative_model_id
            self.reference_field = self.template_id.reference_field
            self.volume_field = self.template_id.volume_field
            self.date_field_for_last_reading = \
                self.template_id.date_field_for_last_reading
            self.negative_field_mapping_json = \
                self.template_id.negative_field_mapping_json

    @api.onchange('use_all_sensors')
    def _onchange_use_all_sensors(self):
        """Clear sensor_ids when use_all_sensors is checked"""
        if self.use_all_sensors:
            self.sensor_ids = [(5, 0, 0)]  # Clear all sensors

    @api.onchange('selection_mode')
    def _onchange_selection_mode(self):
        if self.selection_mode == 'date_range':
            if not self.date_from:
                date_from = fields.Datetime.from_string(fields.Datetime.now())
                self.date_from = fields.Datetime.to_string(
                    date_from - relativedelta(days=7))
            if not self.date_to:
                self.date_to = fields.Datetime.now()
        elif self.selection_mode == 'from_date':
            if not self.date_from and not self.auto_date_from_last_record:
                date_from = fields.Datetime.from_string(fields.Datetime.now())
                self.date_from = fields.Datetime.to_string(
                    date_from - relativedelta(days=30))
            self.date_to = False
        elif self.selection_mode == 'closest_reading':
            if not self.reference_date:
                self.reference_date = fields.Datetime.now()
            self.date_from = False
            self.date_to = False
        else:  # last_reading
            self.date_from = False
            self.date_to = False
            self.reference_date = False

    def _get_sensor_domain(self):
        self.ensure_one()
        domain = []
        # Apply sensor domain filter if provided
        if self.sensor_domain_filter:
            try:
                sensor_filter = safe_eval(self.sensor_domain_filter)
                domain.extend(sensor_filter)
            except Exception as e:
                raise exceptions.UserError(
                    _('Invalid sensor domain filter: %s') % str(e))
        # If not using all sensors, restrict to selected sensor_ids
        if not self.use_all_sensors:
            if not self.sensor_ids:
                raise exceptions.UserError(
                    _('Please select at least one sensor or check '
                      '"Use All Sensors"'))
            domain.append(('id', 'in', self.sensor_ids.ids))
        return domain

    def _get_reading_domain(self):
        self.ensure_one()
        # Get sensors based on use_all_sensors and sensor_domain_filter
        sensor_domain = self._get_sensor_domain()
        sensors = self.env['mdm.measurement.device.sensor'].search(
            sensor_domain)
        if not sensors:
            raise exceptions.UserError(
                _('No sensors found matching the criteria'))
        domain = [('sensor_id', 'in', sensors.ids)]
        if self.selection_mode == 'date_range':
            if not self.date_from or not self.date_to:
                raise exceptions.UserError(
                    _('Date Range mode requires both From Date and To Date'))
            domain.extend([
                ('measurement_time', '>', self.date_from),
                ('measurement_time', '<', self.date_to),
            ])
        elif self.selection_mode == 'from_date':
            if not self.date_from:
                raise exceptions.UserError(
                    _('From Date mode requires a From Date'))
            domain.append(('measurement_time', '>', self.date_from))
        elif self.selection_mode == 'last_reading':
            # Will be handled separately per sensor
            pass
        elif self.selection_mode == 'closest_reading':
            if not self.reference_date:
                raise exceptions.UserError(
                    _('Closest Reading mode requires a Reference Date'))
            # Will be handled separately per sensor
        if self.domain_filter:
            try:
                additional_domain = safe_eval(self.domain_filter)
                domain.extend(additional_domain)
            except Exception as e:
                raise exceptions.UserError(
                    _('Invalid domain filter: %s') % str(e))
        return domain

    def _get_readings(self):
        self.ensure_one()
        # Get sensors based on use_all_sensors and sensor_domain_filter
        sensor_domain = self._get_sensor_domain()
        sensors = self.env['mdm.measurement.device.sensor'].search(
            sensor_domain)
        if not sensors:
            raise exceptions.UserError(
                _('No sensors found matching the criteria'))
        reading_model = self.env['mdm.measurement.device.sensor.reading']
        if self.selection_mode == 'last_reading':
            # Get last reading per sensor
            readings = self.env['mdm.measurement.device.sensor.reading']
            for sensor in sensors:
                last_reading = reading_model.search(
                    [('sensor_id', '=', sensor.id)],
                    order='measurement_time desc',
                    limit=1,
                )
                readings |= last_reading
            # Sort resulting readings by date (oldest first)
            return readings.sorted(key=lambda r: r.measurement_time)
        elif self.selection_mode == 'closest_reading':
            # Get reading closest to reference date per sensor
            readings = self.env['mdm.measurement.device.sensor.reading']
            for sensor in sensors:
                # Search readings before and after reference date
                before = reading_model.search(
                    [('sensor_id', '=', sensor.id),
                     ('measurement_time', '<', self.reference_date)],
                    order='measurement_time desc',
                    limit=1,
                )
                after = reading_model.search(
                    [('sensor_id', '=', sensor.id),
                     ('measurement_time', '>', self.reference_date)],
                    order='measurement_time asc',
                    limit=1,
                )
                # Choose the closest one
                if before and after:
                    ref_dt = fields.Datetime.from_string(self.reference_date)
                    before_dt = fields.Datetime.from_string(
                        before.measurement_time)
                    after_dt = fields.Datetime.from_string(
                        after.measurement_time)
                    if abs((ref_dt - before_dt).total_seconds()) <= \
                            abs((ref_dt - after_dt).total_seconds()):
                        readings |= before
                    else:
                        readings |= after
                elif before:
                    readings |= before
                elif after:
                    readings |= after
            # Sort resulting readings by date (oldest first)
            return readings.sorted(key=lambda r: r.measurement_time)
        else:
            # date_range or from_date
            domain = self._get_reading_domain()
            return reading_model.search(
                domain, order='measurement_time asc')

    def _replace_variables_in_expression(self, expression, reading, context):
        def replacer(match):
            var_path = match.group(1)
            # Special case: $now returns current datetime
            if var_path == 'now':
                now_value = fields.Datetime.now()
                context['now'] = now_value
                return 'now'
            # Check if it's a path with dots (e.g., sensor_id.name)
            if '.' in var_path:
                parts = var_path.split('.')
                var_name = parts[0]
                # Try to get base object from reading
                if hasattr(reading, var_name):
                    obj = getattr(reading, var_name)
                    # Navigate through the path
                    for part in parts[1:]:
                        if hasattr(obj, part):
                            obj = getattr(obj, part)
                        else:
                            _logger.warning(
                                'Path "$%s" invalid at "%s"',
                                var_path, part)
                            return 'None'
                    # Store final value in context with sanitized name
                    safe_name = var_path.replace('.', '_')
                    context[safe_name] = obj
                    return safe_name
                else:
                    _logger.warning(
                        'Base variable "$%s" not found in reading',
                        var_name)
                    return 'None'
            # Simple variable without dots
            # Try to get value from reading first
            if hasattr(reading, var_path):
                value = getattr(reading, var_path)
                context[var_path] = value
                return var_path
            # Then try sensor
            elif hasattr(reading.sensor_id, var_path):
                value = getattr(reading.sensor_id, var_path)
                context[var_path] = value
                return var_path
            # Then try device
            elif hasattr(reading.device_id, var_path):
                value = getattr(reading.device_id, var_path)
                context[var_path] = value
                return var_path
            # If not found, leave as-is and log warning
            else:
                _logger.warning(
                    'Variable "$%s" not found in reading, sensor or device',
                    var_path)
                return 'None'
        return re.sub(r'\$([\w\.]+)', replacer, expression)

    def _evaluate_expression(self, expression, reading):
        if expression is None:
            return None
        # If it's not a string (bool, int, float, etc.), return as-is
        if not isinstance(expression, (str, unicode)):
            return expression
        # If it's an empty string
        if not expression.strip():
            return None
        # If it's an expression with $ variables
        if '$' in expression:
            # Build context with all reading fields
            context = {
                'value': reading.value,
                'measurement_time': reading.measurement_time,
                'sensor_id': reading.sensor_id.id,
                'sensor_name': reading.sensor_id.name,
                'device_id': reading.device_id.id,
                'device_name': reading.device_id.name,
                'reading': reading,
                'sensor': reading.sensor_id,
                'device': reading.device_id,
                'now': fields.Datetime.now(),  # Add current datetime
            }
            # Replace all $variables
            eval_expression = self._replace_variables_in_expression(
                expression, reading, context)
            try:
                # Evaluate with the populated context
                return safe_eval(eval_expression, context, mode='eval',
                                 nocopy=True)
            except Exception as e:
                _logger.error(
                    'Error evaluating expression "%s" (converted to "%s"): %s',
                    expression, eval_expression, str(e))
                raise exceptions.UserError(
                    _('Error evaluating expression "%s": %s') %
                    (expression, str(e)))
        # If it's a plain string without variables, return as-is
        return expression

    def _build_target_values(self, reading):
        self.ensure_one()
        values = {}
        # Parse and apply field mapping JSON
        if self.field_mapping_json:
            try:
                field_mapping = json.loads(self.field_mapping_json)
                for target_field, expression in field_mapping.items():
                    value = self._evaluate_expression(expression, reading)
                    if value is not None:
                        values[target_field] = value
            except ValueError as e:
                raise exceptions.UserError(
                    _('Invalid JSON in Field Mapping: %s') % str(e))
        return values

    def _check_negative_reading(self, reading, values, target_model):
        self.ensure_one()
        if not (self.detect_negative_readings and
                self.negative_model_id and
                self.reference_field and
                self.volume_field and
                self.date_field_for_last_reading):
            return False
        # Get the reference field value from values dict
        ref_value = values.get(self.reference_field)
        new_volume = values.get(self.volume_field)
        if not (ref_value and new_volume is not None):
            return False
        # Search for last reading with same reference, ordered by date field
        last_reading = target_model.search([
            (self.reference_field, '=', ref_value),
        ], order='%s desc' % self.date_field_for_last_reading, limit=1)
        if not last_reading:
            return False
        last_volume = getattr(last_reading, self.volume_field, 0)
        # Check if volume decreased (negative reading)
        if new_volume >= last_volume:
            return False
        # Handle negative reading
        self._create_negative_reading(reading, last_volume, new_volume)
        return True

    def _create_negative_reading(self, reading, last_volume, new_volume):
        """Create a negative reading record."""
        self.ensure_one()
        volume_diff = last_volume - new_volume
        negative_target = self.env[self.negative_model]
        if not self.negative_field_mapping_json:
            return
        neg_mapping = json.loads(self.negative_field_mapping_json)
        neg_values = {}
        # Build values for negative reading
        for field, expr in neg_mapping.items():
            # Replace $volume_diff
            if isinstance(expr, (str, unicode)):
                expr_with_diff = expr.replace(
                    '$volume_diff',
                    str(volume_diff))
                neg_values[field] = (
                    self._evaluate_expression(
                        expr_with_diff, reading))
            else:
                neg_values[field] = expr
        negative_target.create(neg_values)

    # Return dict with:
    # - 'status': 'created', 'negative', or 'error'
    # - 'error': error message (if status is 'error')
    def _process_single_reading(self, reading, target_model):
        self.ensure_one()
        try:
            values = self._build_target_values(reading)
            # Check if negative reading detection is enabled
            if self._check_negative_reading(reading, values, target_model):
                return {'status': 'negative'}
            # Normal creation
            target_model.create(values)
            return {'status': 'created'}
        except Exception as e:
            error_msg = 'Reading %s: %s' % (reading.name, str(e))
            _logger.error('Error transforming reading: %s', error_msg)
            return {'status': 'error', 'error': error_msg}

    def _build_result_message(self, created_count, negative_count,
                              error_count, total_count, errors):
        self.ensure_one()
        message_parts = []
        # Summary section
        if negative_count > 0:
            summary = (
                '<p style="font-size:14px;margin-bottom:15px;">'
                '<b>%s:</b> %d<br/>'
                '<b>%s:</b> %d<br/>'
                '<b>%s:</b> %d<br/>'
                '<b>%s:</b> %d'
                '</p>'
            ) % (
                _('Normal records created'), created_count,
                _('Negative records created'), negative_count,
                _('Errors'), error_count,
                _('Total readings processed'), total_count,
            )
        else:
            summary = (
                '<p style="font-size:14px;margin-bottom:15px;">'
                '<b>%s:</b> %d<br/>'
                '<b>%s:</b> %d<br/>'
                '<b>%s:</b> %d'
                '</p>'
            ) % (
                _('Records created'), created_count,
                _('Errors'), error_count,
                _('Total readings processed'), total_count,
            )
        message_parts.append(summary)
        # Errors section
        if errors:
            # Show first 10 errors
            error_list = ''.join([
                '<li style="color:red;font-weight:bold;">%s</li>' % msg
                for msg in errors[:10]
            ])
            if len(errors) > 10:
                error_list += (
                    '<li style="color:orange;">%s</li>' %
                    _('... and %d more errors') % (len(errors) - 10)
                )
            message_parts.append(
                '<h4 style="margin-top:15px;color:red;">%s</h4><ul>%s</ul>' %
                (_('Errors found'), error_list),
            )
        message = (
            '<div style="font-family:sans-serif">'
            '<p style="font-size:16px;margin-bottom:10px;">'
            '<b style="font-size:18px;color:#2c3e50;">%s</b>'
            '</p>%s</div>'
        ) % (
            _('Transformation Complete'),
            ''.join(message_parts),
        )
        return message

    # Sensor reading -> Target model or negative model
    def action_transform(self):
        self.ensure_one()
        if not self.target_model:
            raise exceptions.UserError(_('Target Model is required'))
        try:
            target_model = self.env[self.target_model]
        except KeyError:
            raise exceptions.UserError(
                _('Target model "%s" does not exist') % self.target_model)
        # Get readings to process
        readings = self._get_readings()
        if not readings:
            raise exceptions.UserError(
                _('No readings found with the specified criteria'))
        # Process all readings
        created_count = 0
        negative_count = 0
        error_count = 0
        errors = []
        for reading in readings:
            result = self._process_single_reading(reading, target_model)
            if result['status'] == 'created':
                created_count += 1
            elif result['status'] == 'negative':
                negative_count += 1
            elif result['status'] == 'error':
                error_count += 1
                errors.append(result['error'])
        # Build and return result message
        message = self._build_result_message(
            created_count, negative_count, error_count,
            len(readings), errors)
        return {
            'type': 'ir.actions.act_window.message',
            'title': _('Transformation Result'),
            'message': message,
            'is_html_message': True,
            'close_button_title': False,
            'buttons': [
                {
                    'type': 'ir.actions.act_window_close',
                    'name': _('Close'),
                },
            ],
        }

    def action_save_as_template(self):
        self.ensure_one()
        self.env['mdm.sensor.reading.transform.template'].create({
            'name': self.name,
            'use_all_sensors': self.use_all_sensors,
            'sensor_ids': [(6, 0, self.sensor_ids.ids)],
            'sensor_domain_filter': self.sensor_domain_filter,
            'target_model_id': self.target_model_id.id,
            'selection_mode': self.selection_mode,
            'auto_date_from_last_record': self.auto_date_from_last_record,
            'target_date_field_id': (
                self.target_date_field_id.id if self.target_date_field_id
                else False
            ),
            'field_mapping_json': self.field_mapping_json,
            'domain_filter': self.domain_filter,
            'detect_negative_readings': self.detect_negative_readings,
            'negative_model_id': (
                self.negative_model_id.id if self.negative_model_id
                else False
            ),
            'reference_field': self.reference_field,
            'volume_field': self.volume_field,
            'date_field_for_last_reading': self.date_field_for_last_reading,
            'negative_field_mapping_json': self.negative_field_mapping_json,
        })
        message = (
            '<div style="font-family:sans-serif">'
            '<p style="font-size:14px;">'
            '%s'
            '</p></div>'
        ) % (_('Template "%s" has been saved successfully') % self.name)
        return {
            'type': 'ir.actions.act_window.message',
            'title': _('Template Saved'),
            'message': message,
            'is_html_message': True,
            'close_button_title': False,
            'buttons': [
                {
                    'type': 'ir.actions.act_window_close',
                    'name': _('Close'),
                },
            ],
        }
