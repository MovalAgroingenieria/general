# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json
import requests
from odoo import models, fields, api, exceptions, _
import logging

_logger = logging.getLogger(__name__)


class BoardGrafana(models.Model):
    _name = "grafana.dashboard.storage"
    _description = "Storage of Grafana Dashboards"

    name = fields.Char(
        string="Dashboard name",
        readonly=False,
        required=True,
    )

    dashboard_title = fields.Char(
        string="Dashboard title",
        compute="_compute_dashboard_title",
        readonly=False,
        help="The title of the embebbed dashboard.",
    )

    dashboard_uid = fields.Char(
        string="Dashboard uid",
        compute="_compute_dashboard_uid",
        readonly=False,
        help="The id of the embebbed dashboard.",
    )

    dashboard_path = fields.Char(
        string="Dashboard path",
        readonly=False,
        compute="_compute_dashboard_path",
    )

    dashboard_json = fields.Text(
        string="JSON Content",
    )

    integrated_dashboard = fields.Boolean(
        string="Integrated Dashboard",
        default=False,
        help="If the dashboard is integrated with a module.",
    )

    integrated_panel_only = fields.Boolean(
        string="Panel only",
        default=False,
        help="If only a panel of the dashboard is integrated.",
    )

    integrated_panel_id = fields.Char(
        string="Panel id",
        help="The id of the panel in the dashboard.",
    )

    frame_width = fields.Char(
        string="Frame width",
        default="100%",
        help="Width of the iframe. Default is 100%.",
    )

    frame_height = fields.Char(
        string="Frame height",
        default="600px",
        help="Height of the iframe. Default is 600px.",
    )

    _sql_constraints = [
        ("name_uniq", "unique(name)", "The dashboard name must be unique!"),
    ]

    @api.depends("dashboard_json")
    def _compute_dashboard_title(self):
        for record in self:
            dashboard_title = dashboard_data = ""
            if record.dashboard_json:
                try:
                    dashboard_data = json.loads(record.dashboard_json)
                except ValueError as e:
                    raise exceptions.UserError(_("Invalid JSON. Dashboard '%s': %s") % (self.name, e))
                dashboard_title = dashboard_data.get("title", "")
            record.dashboard_title = dashboard_title

    @api.depends("dashboard_json")
    def _compute_dashboard_uid(self):
        for record in self:
            dashboard_uid = dashboard_data = ""
            if record.dashboard_json:
                try:
                    dashboard_data = json.loads(record.dashboard_json)
                except ValueError as e:
                    raise exceptions.UserError(_("Invalid JSON. Dashboard '%s': %s") % (self.name, e))
                dashboard_uid = dashboard_data.get("uid", "")
            record.dashboard_uid = dashboard_uid

    @api.depends("dashboard_uid", "dashboard_title", "integrated_panel_only", "integrated_panel_id")
    def _compute_dashboard_path(self):
        for record in self:
            path = ""
            if (record.integrated_panel_only and record.integrated_panel_id and
                    record.dashboard_uid and record.dashboard_title):
                path = "/d-solo/" + record.dashboard_uid + "/" + record.dashboard_title + "?panelId=" + \
                    str(record.integrated_panel_id)
            elif record.dashboard_uid and record.dashboard_title:
                path = "/d/" + record.dashboard_uid + "/" + record.dashboard_title + "?kiosk"
            record.dashboard_path = path

    def action_import_to_grafana(self):
        self.ensure_one()
        # Check json
        dashboard_title = dashboard_uid = dashboard_data = ""
        try:
            dashboard_data = json.loads(self.dashboard_json)
        except ValueError as e:
            raise exceptions.UserError(_("Invalid JSON for dashboard '%s': %s") % (self.name, e))
        dashboard_title = dashboard_data.get("title", "")
        dashboard_uid = dashboard_data.get("uid", "")
        if dashboard_title != self.dashboard_title:
            raise exceptions.UserError(_("Dashboard title '%s' does not match the JSON title '%s'.") %
                                       (self.name, dashboard_title))
        if dashboard_uid != self.dashboard_uid:
            raise exceptions.UserError(_("Dashboard id '%s' does not match the JSON uid '%s'.") %
                                       (self.dashboard_uid, dashboard_uid))
        # Vars
        buttons = [{"type": "ir.actions.act_window_close", "name": _("Close")}]
        message = ""
        # Get config params
        grafana_url = self.env["ir.config_parameter"].sudo().get_param("grafana_integration.grafana_url")
        grafana_api_key = self.env["ir.config_parameter"].sudo().get_param("grafana_integration.grafana_api_key")
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
        _logger.info("Importing dashboard '%s' to Grafana: %s", self.name, endpoint)
        response = requests.post(
            endpoint, headers=headers, data=json.dumps(payload), timeout=15)
        if response.status_code in (200, 202):
            self.integrated_dashboard = True
            _logger.info("Dashboard '%s' imported successfully.", self.name)
            message += _("Dashboard '%s' imported successfully.") % self.name
        else:
            error_msg = response.text or response.reason
            _logger.error("Failed to import dashboard '%s' (status %s): %s",
                self.name, response.status_code, error_msg)
            message += _("Failed to import dashboard '%s'. HTTP %s: %s") % \
                (self.name, response.status_code, error_msg)
        act_window = {
            "type": "ir.actions.act_window.message",
            "title": _("Grafana Dashboard Import"),
            "message": message,
            "is_html_message": True,
            "close_button_title": False,
            "buttons": buttons
            }
        return act_window
