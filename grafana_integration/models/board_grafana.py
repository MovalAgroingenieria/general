# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, _


class BoardGrafana(models.Model):
    _name = "board.grafana"
    _description = "Board Grafana"

    DEFAULT_DASHBOARD_HEIGHT = 800
    WARNING_TITLE = _("Incomplete configuration")
    WARNING_MESSAGE = _("Grafana URL is missing. Please configure the URL in the Parameters.")

    def _default_grafana_frame(self):
        grafana_url = self.env["ir.config_parameter"].sudo().get_param("grafana_integration.grafana_url")
        force_theme = self.env["ir.config_parameter"].sudo().get_param("grafana_integration.grafana_force_theme")
        dashboard_height = self.env["ir.config_parameter"].sudo().get_param(
            "grafana_integration.grafana_dashboard_height")
        dashboard_id = self.env["ir.config_parameter"].sudo().get_param("grafana_integration.grafana_dashboard_id")
        if not grafana_url:
            return f"""
                <div class="alert alert-warning">
                    <strong>{self.WARNING_TITLE}</strong><br/>{self.WARNING_MESSAGE}
                </div>
            """
        if dashboard_id:
            grafana_url = grafana_url + "/d/" + dashboard_id
        if force_theme and force_theme == "light":
            grafana_url = grafana_url + "?theme=light"
        elif force_theme and force_theme == "dark":
            grafana_url = grafana_url + "?theme=dark"
        height = self.DEFAULT_DASHBOARD_HEIGHT
        if dashboard_height:
            height = dashboard_height
        frame_params = 'width="100%" height="' + str(height) + '"'
        frame_layout = '<iframe id="grafana_frame" marginwidth="0" ' + 'marginheight="0" frameborder="no" ' + \
            frame_params + ' src="' + grafana_url + '"></iframe>'
        grafana_frame = frame_layout
        return grafana_frame

    grafana_frame = fields.Text(
        string="Grafana frame",
        default=_default_grafana_frame,
        compute="_compute_grafana_frame",
    )

    def _compute_grafana_frame(self):
        self.grafana_frame = False

    def action_grafana_server(self):
        grafana_url = self.env["ir.config_parameter"].sudo().get_param("grafana_integration.grafana_url")
        if not grafana_url:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": self.WARNING_TITLE,
                    "message": self.WARNING_MESSAGE,
                    "type": "warning",
                    "sticky": False,
                }
            }
        server_url = grafana_url + "/login"
        return {
            "type": "ir.actions.act_url",
            "url": server_url,
            "target": "new",
        }

    def create_grafana_frame(self, frame_src, frame_id, frame_params):
        grafana_url = self.env["ir.config_parameter"].sudo().get_param("grafana_integration.grafana_url")
        if not grafana_url:
            return f"""
                <div class="alert alert-warning">
                    <strong>{self.WARNING_TITLE}</strong><br/>{self.WARNING_MESSAGE}
                </div>
            """
        frame_url = grafana_url + frame_src
        frame_id = frame_id
        frame_layout = '<iframe id="' + frame_id + '" marginwidth="0" ' + 'marginheight="0" frameborder="no"' + \
            frame_params + ' src="' + frame_url + '"></iframe>'
        grafana_frame = frame_layout
        return grafana_frame
