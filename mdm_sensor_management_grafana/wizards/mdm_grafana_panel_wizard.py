# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json
import logging
from collections import OrderedDict

from odoo import _, api, exceptions, fields, models

_logger = logging.getLogger(__name__)

# XML IDs of the full dashboard templates used as base.
_TEMPLATE_XML_IDS = {
    'mono_sensor': (
        'mdm_sensor_management_grafana'
        '.template_mono_sensor_dashboard'
    ),
    'histogram': (
        'mdm_sensor_management_grafana'
        '.template_mono_sensor_histogram_dashboard'
    ),
    'multi_sensor': (
        'mdm_sensor_management_grafana'
        '.template_multi_sensor_dashboard'
    ),
}

class MdmGrafanaPanelWizard(models.TransientModel):
    _name = 'mdm.grafana.panel.wizard'
    _description = 'Create and Import Grafana Panel Wizard'

    def _default_dashboard_uid(self):
        return self.env['board.grafana.dashboard.storage']._default_dashboard_uid()

    # ── Context / read-only ────────────────────────────────────────────────

    sensor_type_id = fields.Many2one(
        comodel_name='mdm.measurement.device.sensor.type',
        string='Sensor Type',
        required=True,
        readonly=True,
    )

    uom_id = fields.Many2one(
        comodel_name='mdm.measurement.device.sensor.uom',
        string='Unit of Measure',
        related='sensor_type_id.uom_id',
        readonly=True,
    )

    # ── Panel type ─────────────────────────────────────────────────────────

    panel_type = fields.Selection(
        selection=[
            ('mono_sensor', 'Mono-Sensor (lines)'),
            ('histogram', 'Mono-Sensor (histogram)'),
            ('multi_sensor', 'Multi-Sensor (lines)'),
        ],
        string='Panel Type',
        required=True,
        default='mono_sensor',
        help=(
            "Mono-Sensor (lines): Time-series line chart showing the "
            "readings of a single sensor over time. Best suited for "
            "monitoring one measurement point in detail (e.g. one flow "
            "meter or one probe channel).\n\n"
            "Mono-Sensor (histogram): Bar chart that groups readings into "
            "time intervals (e.g. daily totals). Useful for aggregated "
            "volume or consumption analysis of a single sensor.\n\n"
            "Multi-Sensor (lines): Time-series line chart that overlays "
            "multiple sensors on the same graph. Use this when a device "
            "has several sensors of the same type (e.g. a Humidity Probe "
            "with multiple measurement channels)."
        ),
    )

    # ── Device / sensor selection ──────────────────────────────────────────

    all_devices = fields.Boolean(
        string='All Devices',
        default=False,
    )

    device_id = fields.Many2one(
        comodel_name='mdm.measurement.device',
        string='Device',
    )

    device_ids = fields.Many2many(
        comodel_name='mdm.measurement.device',
        relation='mdm_grafana_panel_wizard_device_rel',
        column1='wizard_id',
        column2='device_id',
        string='Devices',
    )

    # For mono_sensor / histogram: one sensor
    sensor_id = fields.Many2one(
        comodel_name='mdm.measurement.device.sensor',
        string='Sensor',
    )

    # For multi_sensor: one or more sensors
    sensor_ids = fields.Many2many(
        comodel_name='mdm.measurement.device.sensor',
        relation='mdm_grafana_panel_wizard_sensor_rel',
        column1='wizard_id',
        column2='sensor_id',
        string='Sensors',
    )

    # ── Dashboard metadata ─────────────────────────────────────────────────

    dashboard_name = fields.Char(
        string='Dashboard Name',
        required=True,
    )

    dashboard_title = fields.Char(
        string='Dashboard Title',
        required=True,
    )

    dashboard_uid = fields.Char(
        string='Dashboard UID',
        required=True,
        readonly=True,
        default=_default_dashboard_uid,
    )

    # ── Defaults ───────────────────────────────────────────────────────────

    @api.model
    def default_get(self, fields_list):
        res = super(MdmGrafanaPanelWizard, self).default_get(fields_list)
        sensor_type_id = res.get('sensor_type_id')
        if sensor_type_id:
            sensor_type = self.env[
                'mdm.measurement.device.sensor.type'].browse(sensor_type_id)
            if 'dashboard_name' in fields_list and not res.get('dashboard_name'):
                res['dashboard_name'] = sensor_type.name
            if 'dashboard_title' in fields_list and not res.get(
                    'dashboard_title'):
                res['dashboard_title'] = sensor_type.name
        return res

    # ── Onchange helpers ───────────────────────────────────────────────────

    @api.onchange('all_devices', 'sensor_type_id')
    def _onchange_all_devices(self):

        if self.all_devices and self.sensor_type_id:
            all_devices = self.env['mdm.measurement.device'].search([
                ('sensor_ids.type_id', '=', self.sensor_type_id.id)
            ])
            self.device_ids = all_devices
            self.device_id = False

            # If any device has more than one sensor of this type, force multi_sensor panel type
            sensors_per_device = [
                self.env['mdm.measurement.device.sensor'].search_count([
                    ('device_id', '=', device.id),
                    ('type_id', '=', self.sensor_type_id.id),
                ])
                for device in all_devices
            ]
            if any(count > 1 for count in sensors_per_device):
                self.panel_type = 'multi_sensor'
        elif not self.all_devices:
            self.device_ids = [(5, 0, 0)]

    @api.onchange('panel_type', 'device_id', 'device_ids')
    def _onchange_device_or_panel_type(self):
        """Auto-populate sensor(s) and refresh name/title defaults."""
        self.sensor_id = False
        self.sensor_ids = [(5, 0, 0)]

        if not self.sensor_type_id:
            return

        # ── Multi-device case (All Devices checked) ────────────────────────
        if self.all_devices and self.device_ids:
            sensors = self.env['mdm.measurement.device.sensor'].search([
                ('device_id', 'in', self.device_ids.ids),
                ('type_id', '=', self.sensor_type_id.id),
            ])

            if self.panel_type in ('mono_sensor', 'histogram'):
                self.sensor_ids = sensors
            else:
                self.sensor_ids = sensors

            # Set dashboard title
            if len(self.device_ids) > 1:
                self.dashboard_name = '%s - All Devices' % self.sensor_type_id.name
                self.dashboard_title = '%s - All Devices' % self.sensor_type_id.name
            else:
                device = self.device_ids[:1]
                self.dashboard_name = '%s - %s' % (device.name, self.sensor_type_id.name)
                self.dashboard_title = '%s - %s' % (device.name, self.sensor_type_id.name)

        # ── Single device case ─────────────────────────────────────────────
        elif self.device_id:
            sensors = self.env['mdm.measurement.device.sensor'].search([
                ('device_id', '=', self.device_id.id),
                ('type_id', '=', self.sensor_type_id.id),
            ])

            if self.panel_type in ('mono_sensor', 'histogram'):
                # Single device + mono-sensor: pick one sensor
                self.sensor_id = sensors[:1]
            else:
                # Single device + multi-sensor: pick all sensors from device
                self.sensor_ids = sensors

            self.dashboard_name = '%s - %s' % (
                self.device_id.name, self.sensor_type_id.name)
            self.dashboard_title = '%s - %s' % (
                self.device_id.name, self.sensor_type_id.name)

    # ── JSON generation ────────────────────────────────────────────────────

    def _get_template_key(self):
        return self.panel_type

    def _build_dashboard_json(self):
        """Clone the full dashboard template JSON and pre-set variable defaults.
        """
        self.ensure_one()
        template_key = self._get_template_key()
        template = self.env.ref(_TEMPLATE_XML_IDS[template_key])
        data = json.loads(
            template.dashboard_json, object_pairs_hook=OrderedDict)

        if self.all_devices:
            device_names = [d.name for d in self.device_ids]
        else:
            device_names = [self.device_id.name] if self.device_id else []

        if self.sensor_ids:
            sensor_names = [s.name for s in self.sensor_ids]
        elif self.sensor_id:
            sensor_names = [self.sensor_id.name]
        else:
            sensor_names = []

        sensor_type_name_db = (
            self.with_context(lang=False).sensor_type_id.name
            if self.sensor_type_id else ''
        )

        for var in data.get('templating', {}).get('list', []):
            var_name = var.get('name')

            # Hide variables that are only usded for grafana
            if var_name in ('datasource', 'sensor_type', 'sensor_type_id',
                            'uom_id', 'uom'):
                var['hide'] = 2

            if var_name == 'sensor_type' and self.sensor_type_id:
                var['current'] = {
                    'text': sensor_type_name_db,
                    'value': sensor_type_name_db,
                }
                var['options'] = [{
                    'selected': True,
                    'text': sensor_type_name_db,
                    'value': sensor_type_name_db,
                }]

            elif var_name == 'sensor_type_id' and self.sensor_type_id:
                id_str = str(self.sensor_type_id.id)
                var['type'] = 'constant'
                var['query'] = id_str
                var['current'] = {'text': id_str, 'value': id_str}
                var['options'] = [{'selected': True, 'text': id_str, 'value': id_str}]

            elif var_name == 'devices' and device_names:
                # Visible devices multi-selector: set by name
                var['current'] = {
                    'text': device_names,
                    'value': device_names,
                }

            elif var_name == 'sensors' and sensor_names:
                var['current'] = {
                    'text': sensor_names,
                    'value': sensor_names,
                }

        # Reset id and version so Grafana treats this as a new dashboard.
        data['id'] = 0
        data['version'] = 1

        # Apply legend placement (bottom) and unit to all data panels.
        grafana_unit = (
            self.sensor_type_id.uom_id.name
            if self.sensor_type_id and self.sensor_type_id.uom_id else ''
        )
        for panel in data.get('panels', []):
            # Skip rows and other non-data panel types
            if panel.get('type') == 'row':
                continue
            # Legend → bottom
            legend = panel.get('options', {}).get('legend')
            if legend is not None:
                legend['placement'] = 'bottom'
            # Unit → from UOM grafana_unit field (only if configured)
            if grafana_unit:
                field_defaults = panel.get('fieldConfig', {}).get('defaults')
                if field_defaults is not None:
                    field_defaults['unit'] = grafana_unit

        return json.dumps(data, indent=2)

    @api.multi
    def action_create_and_import(self):
        self.ensure_one()

        # Validation: need either device_id or device_ids
        if not self.all_devices and not self.device_id:
            raise exceptions.UserError(
                _("Please select a device or enable 'All Devices'."))
        if self.all_devices and not self.device_ids:
            raise exceptions.UserError(
                _("Please select at least one device."))

        # Validation: for mono_sensor/histogram need sensor_id (single device)
        # or sensor_ids (all devices with one sensor per device)
        if self.panel_type in ('mono_sensor', 'histogram'):
            if not self.all_devices and not self.sensor_id:
                raise exceptions.UserError(_("Please select a sensor."))
            if self.all_devices and not self.sensor_ids:
                raise exceptions.UserError(
                    _("Please select at least one sensor."))

        # Validation: for multi_sensor need sensor_ids
        if self.panel_type == 'multi_sensor' and not self.sensor_ids:
            raise exceptions.UserError(
                _("Please select at least one sensor."))

        dashboard_json = self._build_dashboard_json()

        _logger.info("Dashboard JSON generated successfully, length: %d",
                     len(dashboard_json))

        storage = self.env['board.grafana.dashboard.storage'].create({
            'name': self.dashboard_name,
            'dashboard_title': self.dashboard_title,
            'dashboard_uid': self.dashboard_uid,
            'dashboard_json': dashboard_json,
        })

        _logger.info("Dashboard storage record created with ID: %s", storage.id)

        # Link the new dashboard to the sensor type so it appears in the
        # 'Grafana Dashboards' stat button on the sensor type form.
        self.sensor_type_id.write({
            'grafana_dashboard_ids': [(4, storage.id)],
        })

        # Call the action from board.grafana.dashboard.storage to import the dashboard to Grafana.
        storage.action_import_to_grafana()

        # Build the Grafana URL directly from the UID to avoid stale ORM
        # cache on dashboard_path (which is written during import but may not
        # yet be reflected in the current environment's cache).
        grafana_url = self.env['ir.values'].get_default(
            'board.grafana.configuration', 'grafana_url')
        url = '%s/d/%s' % (grafana_url or '', self.dashboard_uid)

        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }
