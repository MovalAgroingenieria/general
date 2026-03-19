# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

import requests

from odoo import _, api, exceptions, fields, models

_logger = logging.getLogger(__name__)


class MeasurementDeviceSensorTypeGrafana(models.Model):
    _inherit = 'mdm.measurement.device.sensor.type'

    grafana_dashboard_ids = fields.Many2many(
        comodel_name='board.grafana.dashboard.storage',
        relation='mdm_sensor_type_grafana_dashboard_rel',
        column1='sensor_type_id',
        column2='dashboard_id',
        string='Grafana Dashboards',
    )

    @api.multi
    def action_view_grafana_panels(self):
        self.ensure_one()
        if not self.grafana_dashboard_ids:
            raise exceptions.UserError(
                _("There are no Grafana panels created for this sensor type yet.\n"
                  "Use the 'Create Grafana Panel' button to create one."))
        grafana_url = self.env['ir.values'].get_default(
            'board.grafana.configuration', 'grafana_url')
        # Open the most recently linked dashboard (last in the M2M list).
        dashboard = self.grafana_dashboard_ids[-1]
        dashboard_path = dashboard.dashboard_path.split('?')[0]
        url = (grafana_url or '') + dashboard_path
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    @api.multi
    def action_delete_grafana_panel(self):
        self.ensure_one()
        if not self.grafana_dashboard_ids:
            raise exceptions.UserError(
                _("There are no Grafana panels associated with this sensor type."))
        grafana_url = self.env['ir.values'].get_default(
            'board.grafana.configuration', 'grafana_url')
        grafana_api_key = self.env['ir.values'].get_default(
            'board.grafana.configuration', 'grafana_api_key')
        headers = {
            'Authorization': 'Bearer %s' % (grafana_api_key or ''),
            'Content-Type': 'application/json',
        }
        errors = []
        for dashboard in self.grafana_dashboard_ids:
            uid = dashboard.dashboard_uid
            try:
                response = requests.delete(
                    '%s/api/dashboards/uid/%s' % (grafana_url, uid),
                    headers=headers,
                    timeout=10,
                )
                if response.status_code in (200, 404):
                    # 200 = deleted, 404 = already gone — both are fine
                    _logger.info(
                        "Grafana dashboard '%s' (uid: %s) deleted or not found.",
                        dashboard.name, uid)
                else:
                    errors.append(
                        _("Dashboard '%s': HTTP %s - %s") % (
                            dashboard.name, response.status_code, response.text))
            except Exception as e:
                _logger.warning(
                    "Could not reach Grafana to delete dashboard '%s': %s",
                    dashboard.name, e)
                errors.append(_("Dashboard '%s': %s") % (dashboard.name, e))
        if errors:
            raise exceptions.UserError(
                _("Some dashboards could not be deleted from Grafana:\n%s\n\n"
                  "The Odoo records have NOT been removed. "
                  "Please check the connection and try again.") % '\n'.join(errors))
        # Remove the Odoo storage records and unlink from this sensor type
        dashboards_to_delete = self.grafana_dashboard_ids
        self.grafana_dashboard_ids = [(5, 0, 0)]
        dashboards_to_delete.unlink()

    @api.multi
    def action_open_grafana_panel_wizard(self):
        self.ensure_one()
        sensor_count = self.env['mdm.measurement.device.sensor'].search_count([
            ('type_id', '=', self.id),
        ])
        if not sensor_count:
            raise exceptions.UserError(
                _("Cannot create a Grafana panel for '%s': "
                  "there are no devices or sensors associated with this "
                  "sensor type yet.\n\n"
                  "Please assign at least one sensor of this type to a "
                  "device first.") % self.name)
        return {
            'name': _('Create Grafana Panel'),
            'type': 'ir.actions.act_window',
            'res_model': 'mdm.grafana.panel.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sensor_type_id': self.id,
            },
        }
