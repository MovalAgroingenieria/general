# -*- coding: utf-8 -*-
# 2026 Moval Agroingenieria
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class RemotecontrolAvametImportWizard(models.TransientModel):
    _name = 'remotecontrol.avamet.import.wizard'
    _description = 'AVAMET import wizard'

    remotecontrol_id = fields.Many2one(
        comodel_name='remotecontrol',
        string='Remotecontrol',
        required=True,
        domain=[('is_avamet', '=', True)],
    )

    initial_date = fields.Date(
        string='Initial date',
        default=lambda self: fields.Date.to_string(
            fields.Date.from_string(fields.Date.today()) - timedelta(days=1),
        ),
        help='Default start date written in device/sensor parameters.',
    )

    line_ids = fields.One2many(
        comodel_name='remotecontrol.avamet.import.wizard.line',
        inverse_name='wizard_id',
        string='Available sensors',
    )

    device_line_ids = fields.One2many(
        comodel_name='remotecontrol.avamet.import.wizard.device.line',
        inverse_name='wizard_id',
        string='Available devices',
    )

    station_count = fields.Integer(
        string='Stations found',
        compute='_compute_station_count',
    )

    variable_count = fields.Integer(
        string='Variables found',
        compute='_compute_variable_count',
    )

    selected_count = fields.Integer(
        string='Selected',
        compute='_compute_selection_count',
    )

    not_selected_count = fields.Integer(
        string='Not selected',
        compute='_compute_selection_count',
    )

    status_message = fields.Text(
        string='Status',
        readonly=True,
        help='Messages from the last reload operation.',
    )

    @api.model
    def default_get(self, fields_list):
        values = super(RemotecontrolAvametImportWizard, self).default_get(
            fields_list,
        )
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        if active_model == 'remotecontrol' and active_id:
            values['remotecontrol_id'] = active_id
        return values

    @api.depends('device_line_ids')
    def _compute_station_count(self):
        for wizard in self:
            wizard.station_count = len(wizard.device_line_ids)

    @api.depends('line_ids')
    def _compute_variable_count(self):
        for wizard in self:
            wizard.variable_count = len(wizard.line_ids)

    @api.depends('line_ids', 'line_ids.selected')
    def _compute_selection_count(self):
        for wizard in self:
            selected_lines = wizard.line_ids.filtered(
                lambda line: line.selected,
            )
            wizard.selected_count = len(selected_lines)
            wizard.not_selected_count = (
                len(wizard.line_ids) - len(selected_lines)
            )

    @api.multi
    def _open_self_action(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('AVAMET station import'),
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    @api.multi
    def action_select_all_lines(self):
        self.ensure_one()
        self.line_ids.write({'selected': True})
        return self._open_self_action()

    @api.multi
    def action_deselect_all_lines(self):
        self.ensure_one()
        self.line_ids.write({'selected': False})
        return self._open_self_action()

    @api.multi
    def action_select_all_devices(self):
        self.ensure_one()
        self.device_line_ids.write({'selected': True})
        return self._open_self_action()

    @api.multi
    def action_deselect_all_devices(self):
        self.ensure_one()
        self.device_line_ids.write({'selected': False})
        return self._open_self_action()

    @api.multi
    def _get_or_create_sensor_uom(self, uom_name, uom_short_name):
        self.ensure_one()
        uom_model = self.env['mdm.measurement.device.sensor.uom']
        final_name = (uom_name or 'AVAMET Unknown').strip()
        final_short_name = (uom_short_name or '?').strip()
        sensor_uom = False
        if final_short_name:
            sensor_uom = uom_model.search([
                ('short_name', '=', final_short_name),
            ], limit=1)
        if not sensor_uom:
            sensor_uom = uom_model.search([
                ('name', '=', final_name),
            ], limit=1)
        if not sensor_uom:
            sensor_uom = uom_model.create({
                'name': final_name,
                'short_name': final_short_name,
            })
        return sensor_uom

    @api.multi
    def _get_or_create_sensor_type(self, sensor_name, sensor_uom):
        self.ensure_one()
        sensor_type_model = self.env['mdm.measurement.device.sensor.type']
        type_name = 'AVAMET %s' % sensor_name
        sensor_type = sensor_type_model.search([
            ('name', '=', type_name),
        ], limit=1)
        if sensor_type and sensor_type.uom_id != sensor_uom:
            suffix = sensor_uom.short_name or sensor_uom.name or 'uom'
            type_name = 'AVAMET %s (%s)' % (sensor_name, suffix)
            sensor_type = sensor_type_model.search([
                ('name', '=', type_name),
            ], limit=1)
        if not sensor_type:
            sensor_type = sensor_type_model.create({
                'name': type_name,
                'uom_id': sensor_uom.id,
            })
        return sensor_type

    @api.multi
    def action_reload_stations(self):
        self.ensure_one()
        if not self.remotecontrol_id:
            raise UserError(_('Remotecontrol is required.'))
        value_date = fields.Date.from_string(
            self.initial_date or fields.Date.today(),
        )
        messages = []
        try:
            stations = (
                self.remotecontrol_id.avamet_fetch_station_catalog()
            )
            messages.append(
                u'✓ Found %d stations for %s' % (
                    len(stations),
                    self.initial_date or fields.Date.today(),
                ),
            )
        except Exception as error:
            messages.append(
                u'✗ Failed to fetch stations: %s' % error,
            )
            self.status_message = u'\n'.join(messages)
            raise UserError(
                _('Station catalog fetch failed: %s') % error,
            )
        self.line_ids.unlink()
        self.device_line_ids.unlink()
        line_model = self.env['remotecontrol.avamet.import.wizard.line']
        device_line_model = self.env[
            'remotecontrol.avamet.import.wizard.device.line'
        ]
        station_count = 0
        variable_count = 0
        error_count = 0
        for station in stations:
            station_id = station.get('station_id')
            if not station_id:
                continue
            device_line = False
            try:
                variables = (
                    self.remotecontrol_id.avamet_fetch_station_variables(
                        station_id,
                        value_date=value_date,
                    )
                )
                if variables:
                    station_count += 1
                    variable_count += len(variables)
                    messages.append(
                        u'  • Station %s: %d variables' % (
                            station_id,
                            len(variables),
                        ),
                    )
                    device_line = device_line_model.create({
                        'wizard_id': self.id,
                        'selected': True,
                        'station_id': station_id,
                        'station_name': station.get('name'),
                    })
                else:
                    messages.append(
                        u'  ⚠ Station %s: no variables found' % station_id,
                    )
                    error_count += 1
            except Exception as error:
                messages.append(
                    u'  ✗ Station %s: %s' % (
                        station_id,
                        self._format_reload_error(error),
                    ),
                )
                error_count += 1
                variables = []
            if device_line:
                for variable in variables:
                    line_model.create({
                        'wizard_id': self.id,
                        'device_line_id': device_line.id,
                        'selected': True,
                        'station_id': station_id,
                        'station_name': station.get('name'),
                        'api_field': variable.get('api_field'),
                        'sensor_name': variable.get('sensor_name'),
                        'sample_value': variable.get('sample_value'),
                        'uom_name': variable.get('uom_name'),
                        'uom_short_name': variable.get('uom_short_name'),
                    })
        messages.append(
            u'\nSummary: %d stations, %d variables, %d errors' % (
                station_count,
                variable_count,
                error_count,
            ),
        )
        self.status_message = u'\n'.join(messages)
        return self._open_self_action()

    @api.multi
    def action_clear_data(self):
        self.ensure_one()
        self.line_ids.unlink()
        self.device_line_ids.unlink()
        self.status_message = False
        return self._open_self_action()

    @api.model
    def _format_reload_error(self, error):
        error_message = u'%s' % error
        if '403 Client Error' in error_message:
            return _('Forbidden: no permission to read historic data.')
        if '400 Client Error' in error_message:
            return _('Bad request: invalid historic range or station data.')
        return error_message

    @api.multi
    def action_create_devices(self):
        self.ensure_one()
        selected_device_lines = self.device_line_ids.filtered(
            lambda line: line.selected,
        )
        selected_lines = self.line_ids.filtered(
            lambda line: (
                line.selected and
                line.device_line_id and
                line.device_line_id in selected_device_lines
            ),
        )
        if not selected_lines:
            raise UserError(_('Please select at least one sensor.'))
        signatures = set()
        for line in selected_lines:
            if not line.api_field or not line.sensor_name:
                raise UserError(
                    _('Selected lines require API field and sensor name.'),
                )
            signature = (line.station_id, line.sensor_name)
            if signature in signatures:
                raise UserError(
                    _('Duplicated sensor name for station %s: %s') % (
                        line.station_id,
                        line.sensor_name,
                    ),
                )
            signatures.add(signature)
        created_device_ids = []
        device_model = self.env['mdm.measurement.device']
        sensor_model = self.env['mdm.measurement.device.sensor']
        device_map = {}
        sorted_lines = selected_lines.sorted(
            key=lambda line: (line.station_id or '', line.api_field or ''),
        )
        for line in sorted_lines:
            device = device_map.get(line.station_id)
            metadata = self.remotecontrol_id.avamet_fetch_station_metadata(
                line.station_id,
            )
            municipality = (
                metadata.get('Municipio') or metadata.get('Municipi')
            )
            province = metadata.get('Provincia') or metadata.get('Provincia')
            if not device:
                device_name = 'AVAMET %s' % line.station_id
                start_date = self.initial_date or ''
                device_params = {
                    'station_id': line.station_id,
                    'station_name': line.station_name,
                    'start_date': start_date,
                }
                device = device_model.search([
                    ('name', '=', device_name),
                ], limit=1)
                try:
                    agroclimatic_category = self.env.ref(
                        'mdm_sensor_management.'
                        'mdm_measurement_device_category_agroclimatic_station',
                    )
                    category_id = agroclimatic_category.id
                except Exception:
                    category_id = False
                device_vals = {
                    'name': device_name,
                    'description': line.station_name,
                    'location': ', '.join(
                        filter(None, [municipality, province]),
                    ),
                    'remotecontrol_id': self.remotecontrol_id.id,
                    'category_id': category_id,
                    'remotecontrol_params': json.dumps(device_params),
                }
                if device:
                    device.write(device_vals)
                else:
                    device = device_model.create(device_vals)
                created_device_ids.append(device.id)
                device_map[line.station_id] = device
            sensor = sensor_model.search([
                ('device_id', '=', device.id),
                ('name', '=', line.sensor_name),
            ], limit=1)
            sensor_uom = self._get_or_create_sensor_uom(
                line.uom_name,
                line.uom_short_name,
            )
            sensor_type = self._get_or_create_sensor_type(
                line.sensor_name,
                sensor_uom,
            )
            sensor_params = {
                'api_field': line.api_field,
                'start_date': self.initial_date or '',
            }
            sensor_vals = {
                'device_id': device.id,
                'name': line.sensor_name,
                'type_id': sensor_type.id,
                'remotecontrol_params': json.dumps(sensor_params),
            }
            if sensor:
                sensor.write(sensor_vals)
            else:
                sensor_model.create(sensor_vals)
        action_record = self.env.ref(
            'mdm_sensor_management.mdm_measurement_device_action',
        )
        return {
            'action_id': action_record.id,
            'device_count': len(created_device_ids),
        }

    @api.multi
    def action_apply_and_create(self, selected_sensor_ids,
                                selected_device_ids, sensor_edits=None):
        """Apply JS-side selections and inline edits, then create devices.

        Called by the AvametImport JS client action widget.

        :param selected_sensor_ids: list of int IDs for lines to select
        :param selected_device_ids: list of int IDs for device lines to select
        :param sensor_edits: dict {str(id): {sensor_name, uom_name,
                             uom_short_name}} — from inline table edits
        """
        self.ensure_one()
        selected_sensors = set(selected_sensor_ids)
        selected_devices = set(selected_device_ids)
        if sensor_edits:
            for line in self.line_ids:
                edits = sensor_edits.get(str(line.id))
                if not edits:
                    continue
                vals = {}
                if edits.get('sensor_name') is not None:
                    vals['sensor_name'] = edits['sensor_name']
                if edits.get('uom_name') is not None:
                    vals['uom_name'] = edits['uom_name']
                if edits.get('uom_short_name') is not None:
                    vals['uom_short_name'] = edits['uom_short_name']
                if vals:
                    line.write(vals)
        for line in self.line_ids:
            line.selected = line.id in selected_sensors
        for device_line in self.device_line_ids:
            device_line.selected = device_line.id in selected_devices
        return self.action_create_devices()

    @api.multi
    def check_existing(self):
        """Return which wizard lines correspond to already-existing records.

        Uses two bulk searches (one for devices, one for sensors) to avoid
        per-station round-trips.

        :returns: dict with 'device_line_ids' and 'sensor_line_ids' — lists of
                  wizard line IDs that map to already-existing DB records.
        """
        self.ensure_one()
        device_model = self.env['mdm.measurement.device']
        sensor_model = self.env['mdm.measurement.device.sensor']

        # Map expected device name -> device_line_id
        name_to_dl_id = {}
        for dl in self.device_line_ids:
            name_to_dl_id['AVAMET %s' % dl.station_id] = dl.id

        if not name_to_dl_id:
            return {'device_line_ids': [], 'sensor_line_ids': []}

        # Bulk search for matching devices
        devices = device_model.search(
            [('name', 'in', name_to_dl_id.keys())])

        existing_device_line_ids = []
        device_id_to_dl_id = {}
        for device in devices:
            dl_id = name_to_dl_id.get(device.name)
            if dl_id:
                existing_device_line_ids.append(dl_id)
                device_id_to_dl_id[device.id] = dl_id

        if not device_id_to_dl_id:
            return {
                'device_line_ids': existing_device_line_ids,
                'sensor_line_ids': [],
            }

        # Build mapping: device_line_id -> list of sensor wizard lines
        dl_to_sensor_lines = {}
        for sl in self.line_ids:
            if sl.device_line_id:
                dl_to_sensor_lines.setdefault(sl.device_line_id.id, []).append(sl)

        # Bulk search for all sensors under the matching devices
        existing_sensors = sensor_model.search(
            [('device_id', 'in', list(device_id_to_dl_id.keys()))])
        existing_sensor_keys = set()
        for s in existing_sensors:
            existing_sensor_keys.add((s.device_id.id, s.name))

        # Check which sensor wizard lines already exist
        existing_sensor_line_ids = []
        for device in devices:
            dl_id = device_id_to_dl_id.get(device.id)
            for sl in dl_to_sensor_lines.get(dl_id, []):
                if (device.id, sl.sensor_name) in existing_sensor_keys:
                    existing_sensor_line_ids.append(sl.id)

        return {
            'device_line_ids': existing_device_line_ids,
            'sensor_line_ids': existing_sensor_line_ids,
        }


class RemotecontrolAvametImportWizardLine(models.TransientModel):
    _name = 'remotecontrol.avamet.import.wizard.line'
    _description = 'AVAMET import wizard line'
    _order = 'station_name, sensor_name, api_field'

    @api.multi
    def set_selected(self, ref_value=True):
        self.write({'selected': bool(ref_value)})
        return True

    wizard_id = fields.Many2one(
        comodel_name='remotecontrol.avamet.import.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )

    device_line_id = fields.Many2one(
        comodel_name='remotecontrol.avamet.import.wizard.device.line',
        string='Device line',
        ondelete='cascade',
    )

    selected = fields.Boolean(
        string='Select',
        default=True,
    )

    station_id = fields.Char(
        string='Station ID',
        required=True,
    )

    station_name = fields.Char(
        string='Station',
        required=True,
    )

    api_field = fields.Char(
        string='API field',
        readonly=True,
    )

    sensor_name = fields.Char(
        string='Sensor name',
    )

    sample_value = fields.Char(
        string='Sample value',
        readonly=True,
    )

    uom_name = fields.Char(
        string='UOM',
        default='AVAMET Unknown',
    )

    uom_short_name = fields.Char(
        string='UOM short',
        default='?',
    )


class RemotecontrolAvametImportWizardDeviceLine(models.TransientModel):
    _name = 'remotecontrol.avamet.import.wizard.device.line'
    _description = 'AVAMET import wizard device line'
    _order = 'station_name, station_id'

    @api.multi
    def action_select_all_sensors(self):
        self.ensure_one()
        self.sensor_line_ids.write({'selected': True})
        self.selected = True
        return self.wizard_id._open_self_action()

    @api.multi
    def action_deselect_all_sensors(self):
        self.ensure_one()
        self.sensor_line_ids.write({'selected': False})
        self.selected = False
        return self.wizard_id._open_self_action()

    @api.multi
    def action_remove_device_line(self):
        self.ensure_one()
        wizard = self.wizard_id
        self.unlink()
        return wizard._open_self_action()

    wizard_id = fields.Many2one(
        comodel_name='remotecontrol.avamet.import.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )

    selected = fields.Boolean(
        string='Select',
        default=True,
    )

    station_id = fields.Char(
        string='Station ID',
        required=True,
    )

    station_name = fields.Char(
        string='Station',
        required=True,
    )

    sensor_line_ids = fields.One2many(
        comodel_name='remotecontrol.avamet.import.wizard.line',
        inverse_name='device_line_id',
        string='Sensors',
    )

    sensor_total = fields.Integer(
        string='Sensors',
        compute='_compute_sensor_count',
    )

    sensor_selected = fields.Integer(
        string='Selected sensors',
        compute='_compute_sensor_count',
    )

    @api.depends('sensor_line_ids', 'sensor_line_ids.selected')
    def _compute_sensor_count(self):
        for line in self:
            selected_lines = line.sensor_line_ids.filtered(
                lambda sensor_line: sensor_line.selected,
            )
            line.sensor_total = len(line.sensor_line_ids)
            line.sensor_selected = len(selected_lines)
