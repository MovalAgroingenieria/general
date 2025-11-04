# -*- coding: utf-8 -*-
# 2022 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models, fields, exceptions, _


class BoardGrafana(models.Model):
    _name = 'board.grafana'
    _description = "Board Grafana"

    DEFAULT_DASHBOARD_HEIGHT = 800

    def _default_grafana_frame(self):
        grafana_url = self.env['ir.values'].get_default(
            'board.grafana.configuration', 'grafana_url')
        grafana_dashboard_height = self.env['ir.values'].get_default(
            'board.grafana.configuration', 'grafana_dashboard_height')
        grafana_dashboard_uid = self.env['ir.values'].get_default(
            'board.grafana.configuration', 'grafana_dashboard_uid')
        if (not grafana_url):
            raise exceptions.ValidationError(
                _('The grafana configuration parameters have not been set.'))
        url = grafana_url
        if grafana_dashboard_uid:
            url = url + '/d/' + grafana_dashboard_uid
        else:
            url = url + '/dashboards'
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
