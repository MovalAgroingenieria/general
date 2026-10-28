# -*- coding: utf-8 -*-
# 2022 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models, fields, exceptions, _
from odoo.tools import html_escape


class BoardGrafana(models.Model):
    _name = 'board.grafana'
    _description = "Board Grafana"

    DEFAULT_DASHBOARD_HEIGHT = 800

    def _default_grafana_frame(self):
        grafana_dashboard_height = self.env['ir.values'].get_default(
            'board.grafana.configuration', 'grafana_dashboard_height')
        url = self._get_grafana_home_url()
        if not url:
            raise exceptions.ValidationError(
                _('The grafana configuration parameters have not been set.'))
        # Does not allow to browse dashboards
        # url = url + '?kiosk'
        height = self.DEFAULT_DASHBOARD_HEIGHT
        if grafana_dashboard_height:
            height = grafana_dashboard_height
        frame_params = 'width="100%" height="' + str(height) + '"'
        frame_layout = '<iframe id="grafana_frame" marginwidth="0" ' + \
            'marginheight="0" frameborder="no" ' + \
            frame_params + ' src="' + url + '"></iframe>'
        grafana_frame = frame_layout
        return grafana_frame

    grafana_frame = fields.Text(
        string='Grafana frame',
        default=_default_grafana_frame,
        compute='_compute_grafana_frame')

    @api.multi
    def _compute_grafana_frame(self):
        self.grafana_frame = False

    @api.model
    def _get_grafana_home_url(self):
        values_model = self.env['ir.values']
        grafana_url = values_model.get_default(
            'board.grafana.configuration', 'grafana_url')
        grafana_dashboard_uid = values_model.get_default(
            'board.grafana.configuration', 'grafana_dashboard_uid')
        url = False
        if grafana_url and grafana_dashboard_uid:
            url = grafana_url + '/d/' + grafana_dashboard_uid
        elif grafana_url:
            url = grafana_url + '/dashboards'
        return url

    @api.model
    def is_grafana_navbar_button_visible(self):
        # Follows the module ACLs, so portal users never get the button
        show_navbar_button = self.env['ir.values'].get_default(
            'board.grafana.configuration', 'grafana_show_navbar_button')
        return bool(show_navbar_button) and self.check_access_rights(
            'read', raise_exception=False)

    @api.model
    def get_grafana_panel_frame(self):
        url = self._get_grafana_home_url()
        if url:
            frame = (
                '<iframe class="o_grafana_panel_frame" src="%s" '
                'allow="fullscreen" frameborder="0"></iframe>'
            ) % html_escape(url)
        else:
            frame = (
                '<div class="o_grafana_panel_alert">'
                '<div class="alert alert-info" role="alert">'
                '<h4>%s</h4><p>%s</p>'
                '</div></div>') % (
                html_escape(_('Grafana is not configured')),
                html_escape(_('The Grafana URL has not been set. Please '
                              'ask an administrator to configure it in '
                              'Dashboards > Grafana > Settings.')))
        return frame

    @api.multi
    def action_go_to_grafana_server(self):
        grafana_url = self.env['ir.values'].get_default(
            'board.grafana.configuration', 'grafana_url')
        if (not grafana_url):
            raise exceptions.ValidationError(
                _('The grafana configuration parameters have not been set.'))
        server_url = grafana_url + '/login'
        return {
            'type': 'ir.actions.act_url',
            'url': server_url,
            'target': 'new',
        }

    def create_grafana_frame(self, frame_src, frame_id, frame_params):
        grafana_url = self.env['ir.values'].get_default(
            'board.grafana.configuration', 'grafana_url')
        if (not grafana_url):
            raise exceptions.ValidationError(
                _('The grafana configuration parameters have not been set.'))
        frame_url = grafana_url + frame_src
        frame_id = frame_id
        frame_layout = '<iframe id="' + frame_id + '" marginwidth="0" ' + \
            'marginheight="0" frameborder="no"' + \
            frame_params + ' src="' + frame_url + '"></iframe>'
        grafana_frame = frame_layout
        return grafana_frame
