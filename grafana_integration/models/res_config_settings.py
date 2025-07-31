# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, exceptions, _

class BoardGrafanaConfiguration(models.TransientModel):
    _inherit = 'res.config.settings'
    _description = 'Configuration of Grafana'

    DEFAULT_DASHBOARD_HEIGHT = 800

    grafana_url_raw = fields.Char(
        string='URL',
        config_parameter='grafana_integration.grafana_url_raw',
        help='The URL of grafana host.',
    )

    grafana_url = fields.Char(
        compute="_compute_grafana_url",
        config_parameter='grafana_integration.grafana_url',
    )

    grafana_force_theme = fields.Selection(
        string="Theme",
        config_parameter='grafana_integration.grafana_force_theme',
        selection=[
            ('light', 'Light'),
            ('dark', 'Dark'),],
        help="Overwrite Grafana theme."
    )

    grafana_api_key = fields.Char(
        string="Grafana API Key",
        config_parameter='grafana_integration.grafana_api_key',
    )

    grafana_default_datasource = fields.Char(
        string="Default datasource",
        config_parameter='grafana_integration.grafana_default_datasource',
        help="The default datasource.",
    )

    grafana_dashboard_height = fields.Integer(
        string='Height (px)',
        config_parameter='grafana_integration.grafana_dashboard_height',
        help='Height of dashboard, in pixels.',
    )

    grafana_dashboard_id = fields.Char(
        string='Id',
        config_parameter='grafana_integration.grafana_dashboard_id',
        help='The id of the embebbed dashboard (if not set the default dashboard configured in Grafana will be used).'
    )

    grafana_notice = fields.Boolean(
        string="Grafana Notice",
        default=False,
        readonly=True,
    )

    @api.depends('grafana_url_raw', 'grafana_force_theme')
    def _compute_grafana_url(self):
        for record in self:
            url = record.grafana_url_raw
            if url:
                if not url.startswith('http'):
                    raise exceptions.ValidationError(_('The URL has to start with http'))
            if url and url.endswith('/'):
                url = url.rstrip('/')
            record.grafana_url = url

    def action_go_to_grafana_server(self):
        self.ensure_one()
        grafana_url = self.grafana_url
        server_url = grafana_url + '/login'
        return {
            'type': 'ir.actions.act_url',
            'url': server_url,
            'target': 'new',
        }
