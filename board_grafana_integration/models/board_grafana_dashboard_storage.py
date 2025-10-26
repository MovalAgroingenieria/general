# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json
import requests
import logging
import random
import string
from collections import OrderedDict
from odoo import models, fields, api, exceptions, _

_logger = logging.getLogger(__name__)


class BoardGrafana(models.Model):
    _name = "board.grafana.dashboard.storage"
    _description = "Storage of Grafana Dashboards"

    def _default_dashboard_uid(self):
        chars = string.ascii_letters + string.digits
        dashboard_uid = ''.join(random.choice(chars) for _ in range(10))
        return dashboard_uid

    name = fields.Char(
        string="Dashboard name",
        readonly=False,
        required=True)

    dashboard_title = fields.Char(
        string="Dashboard title",
        required=True,
        help="The title of the embebbed dashboard.")

    dashboard_uid = fields.Char(
        string="Dashboard uid",
        required=True,
        default=_default_dashboard_uid,
        help="The id of the embebbed dashboard.")

    dashboard_path = fields.Char(
        string="Dashboard path",
        compute="_compute_dashboard_path")

    dashboard_json = fields.Text(
        string="JSON Content",
        required=True,
        help="The JSON content of the Grafana dashboard.")

    integrated_dashboard = fields.Boolean(
        string="Integrated Dashboard",
        default=False,
        help="If the dashboard is integrated with a module.")

    integrated_panel_only = fields.Boolean(
        string="Panel only",
        default=False,
        help="If only a panel of the dashboard is integrated.")

    integrated_panel_id = fields.Char(
        string="Panel id",
        help="The id of the panel in the dashboard.")

    frame_width = fields.Char(
        string="Frame width",
        default="100%",
        help="Width of the iframe. Default is 100%.")

    frame_height = fields.Char(
        string="Frame height",
        default="600px",
        help="Height of the iframe. Default is 600px.")

    _sql_constraints = [
        ('name_uniq', 'unique(name)',
         'The dashboard name must be unique!'),
    ]

    @api.depends("dashboard_uid", "dashboard_title",
                 "integrated_panel_only", "integrated_panel_id")
    def _compute_dashboard_path(self):
        for record in self:
            path = ""
            if (record.integrated_panel_only and record.integrated_panel_id and
                    record.dashboard_uid and record.dashboard_title):
                path = "/d-solo/" + record.dashboard_uid + '/' + \
                    record.dashboard_title + "?panelId=" + \
                    str(record.integrated_panel_id)
            elif record.dashboard_uid and record.dashboard_title:
                path = "/d/" + record.dashboard_uid + '/' + \
                    record.dashboard_title + "?kiosk"
            record.dashboard_path = path

    @api.multi
    def action_import_to_grafana(self):
        self.ensure_one()
        dashboard_data = ""
        try:
            dashboard_data = json.loads(self.dashboard_json)
        except ValueError as e:
            raise exceptions.UserError(_(
                "Invalid JSON for dashboard '%s': %s") % (self.name, e))
        # Vars
        buttons = [{'type': 'ir.actions.act_window_close', 'name': _('Close')}]
        message = ""
        # Get config params
        grafana_url = self.env['ir.values'].get_default(
            'board.grafana.configuration', 'grafana_url')
        grafana_api_key = self.env['ir.values'].get_default(
            'board.grafana.configuration', 'grafana_api_key')
        if not grafana_url or not grafana_api_key:
            raise exceptions.UserError(_("Grafana URL or API key not found."))
        # Construct headers
        headers = {
            "Authorization": "Bearer %s" % grafana_api_key,
            "Content-Type": "application/json",
        }
        endpoint = grafana_url + "/api/dashboards/db"
        # Prepare payload
        payload = {"dashboard": dashboard_data, "overwrite": True, }
        _logger.info("Importing dashboard '%s' to Grafana: %s",
                     self.name, endpoint)
        response = requests.post(
            endpoint, headers=headers, data=json.dumps(payload), timeout=15)
        if response.status_code in (200, 202):
            self.integrated_dashboard = True
            _logger.info("Dashboard '%s' imported successfully.", self.name)
            message += _("Dashboard '%s' imported successfully.") % self.name
            # Delete kiosk param for opening in Grafana (allow editing)
            dashboard_path = self.dashboard_path.split('?')[0]
            imported_dashboard_url = grafana_url + dashboard_path
            # Add link to open in Grafana
            message += "<br/><br/>"
            message += _("<a href='%s'>Open in Grafana</a>") % \
                imported_dashboard_url
        else:
            error_msg = response.text or response.reason
            _logger.error(
                "Failed to import dashboard '%s' (status %s): %s",
                self.name, response.status_code, error_msg)
            message += _("Failed to import dashboard '%s'. HTTP %s: %s") % \
                (self.name, response.status_code, error_msg)
        act_window = {
            'type': 'ir.actions.act_window.message',
            'title': _('Grafana Dashboard Import'),
            'message': message,
            'is_html_message': True,
            'close_button_title': False,
            'buttons': buttons
            }
        return act_window

    @api.multi
    def write(self, vals):
        if 'dashboard_title' in vals or 'dashboard_uid' in vals:
            try:
                dashboard_data = json.loads(
                    self.dashboard_json, object_pairs_hook=OrderedDict)
            except ValueError as e:
                raise exceptions.UserError(_(
                    "Invalid JSON. Dashboard '%s': %s") % (self.name, e))
            if 'dashboard_title' in vals:
                dashboard_data["title"] = vals['dashboard_title']
            if 'dashboard_uid' in vals:
                dashboard_data["uid"] = vals['dashboard_uid']
            self.dashboard_json = json.dumps(dashboard_data, indent=2)
        return super(BoardGrafana, self).write(vals)

    @api.model
    def create(self, vals):
        try:
            dashboard_data = json.loads(
                vals['dashboard_json'], object_pairs_hook=OrderedDict)
        except ValueError as e:
            raise exceptions.UserError(_(
                "Invalid JSON. Dashboard '%s': %s") % (vals['name'], e))
        dashboard_data["title"] = vals['dashboard_title']
        dashboard_data["uid"] = vals['dashboard_uid']
        vals['dashboard_json'] = json.dumps(dashboard_data, indent=2)
        return super(BoardGrafana, self).create(vals)

    @api.multi
    def copy(self, default=None):
        default = dict(default or {})
        base_name = self.name
        existing_copies = self.search_count(
            [('name', 'ilike', base_name + '%')])
        new_name = "%s (%d)" % (base_name, existing_copies)
        new_dashboard_uid = self._default_dashboard_uid()
        default['name'] = new_name
        default['dashboard_uid'] = new_dashboard_uid
        return super(BoardGrafana, self).copy(default)
