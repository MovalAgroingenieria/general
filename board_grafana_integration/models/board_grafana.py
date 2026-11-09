# -*- coding: utf-8 -*-
# 2022 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
import json
import logging
import time
import urllib
import urlparse

from odoo import api, models, fields, exceptions, _
from odoo.tools import html_escape

_logger = logging.getLogger(__name__)

try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
except ImportError:
    _logger.debug('Cannot import cryptography')


class BoardGrafana(models.Model):
    _name = 'board.grafana'
    _description = "Board Grafana"

    DEFAULT_DASHBOARD_HEIGHT = 800
    AUTH_ROUTE = '/board_grafana/auth'
    # The Grafana web client keeps the token while it is open and has no
    # way to refresh it: it must outlive a working day
    JWT_LIFETIME = 12 * 3600

    def _default_grafana_frame(self):
        grafana_dashboard_height = self.env['ir.values'].get_default(
            'board.grafana.configuration', 'grafana_dashboard_height')
        url = False
        if self._get_grafana_url():
            url = html_escape(
                self.get_grafana_auth_url(self._get_grafana_home_path()))
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
    def _get_grafana_url(self):
        grafana_url = self.env['ir.values'].get_default(
            'board.grafana.configuration', 'grafana_url')
        return (grafana_url or '').rstrip('/')

    @api.model
    def _get_grafana_home_path(self):
        grafana_dashboard_uid = self.env['ir.values'].get_default(
            'board.grafana.configuration', 'grafana_dashboard_uid')
        path = '/dashboards'
        if grafana_dashboard_uid:
            path = '/d/' + grafana_dashboard_uid
        return path

    @api.model
    def get_grafana_auth_url(self, path):
        # Odoo URL that signs the user in to Grafana and opens the path:
        # the token is created when the URL is opened, so it never expires
        # in a page, an iframe or a stored field
        return '%s?%s' % (
            self.AUTH_ROUTE,
            urllib.urlencode({'path': (path or '').encode('utf-8')}))

    @api.model
    def _get_grafana_path(self, path):
        # Also accepts full Grafana URLs (e.g. the page shown in the side
        # panel). Anything outside Grafana leads to its home page, so the
        # route can not be used as an open redirect.
        grafana_url = self._get_grafana_url()
        path = path or ''
        if grafana_url and path.startswith(grafana_url + '/'):
            path = path[len(grafana_url):]
        if not path.startswith('/') or path.startswith('//') or \
                '\\' in path:
            path = self._get_grafana_home_path()
        parts = urlparse.urlsplit(path)
        # Drops the token of a previous sign-in kept in a Grafana URL
        params = [
            param for param in parts.query.split('&')
            if param and not param.startswith('auth_token=')]
        return urlparse.urlunsplit(
            ('', '', parts.path, '&'.join(params), parts.fragment))

    @api.model
    def _get_grafana_signed_url(self, path):
        grafana_url = self._get_grafana_url()
        url = False
        if grafana_url:
            path = self._get_grafana_path(path)
            token = self._get_grafana_jwt()
            if token:
                parts = urlparse.urlsplit(path)
                query = '&'.join(
                    [param for param in [parts.query] if param] +
                    ['auth_token=' + token])
                path = urlparse.urlunsplit(
                    ('', '', parts.path, query, parts.fragment))
            url = grafana_url + path
        return url

    @api.model
    def _get_grafana_jwt(self):
        settings_model = self.env['board.grafana.configuration']
        login = settings_model._get_grafana_jwt_login()
        private_key = settings_model._get_grafana_jwt_private_key()
        token = False
        if login and private_key:
            now = int(time.time())
            header = {'alg': 'RS256', 'typ': 'JWT'}
            claims = {
                'iss': settings_model.JWT_ISSUER,
                'sub': login,
                'iat': now,
                'exp': now + self.JWT_LIFETIME,
            }
            signing_input = '%s.%s' % (
                self._encode_jwt_segment(json.dumps(header)),
                self._encode_jwt_segment(json.dumps(claims)))
            signature = private_key.sign(
                signing_input, padding.PKCS1v15(), hashes.SHA256())
            token = '%s.%s' % (
                signing_input, self._encode_jwt_segment(signature))
        return token

    @api.model
    def _encode_jwt_segment(self, value):
        return base64.urlsafe_b64encode(value).rstrip('=')

    @api.model
    def is_grafana_navbar_button_visible(self):
        # Follows the module ACLs, so portal users never get the button
        show_navbar_button = self.env['ir.values'].get_default(
            'board.grafana.configuration', 'grafana_show_navbar_button')
        return bool(show_navbar_button) and self.check_access_rights(
            'read', raise_exception=False)

    @api.model
    def get_grafana_panel_frame(self):
        if self._get_grafana_url():
            url = self.get_grafana_auth_url(self._get_grafana_home_path())
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
        if not self._get_grafana_url():
            raise exceptions.ValidationError(
                _('The grafana configuration parameters have not been set.'))
        # Signed in as the Grafana user of the automatic login; without it,
        # Grafana shows its own login page
        return {
            'type': 'ir.actions.act_url',
            'url': self.get_grafana_auth_url(self._get_grafana_home_path()),
            'target': 'new',
        }

    def create_grafana_frame(self, frame_src, frame_id, frame_params):
        grafana_url = self.env['ir.values'].get_default(
            'board.grafana.configuration', 'grafana_url')
        if (not grafana_url):
            raise exceptions.ValidationError(
                _('The grafana configuration parameters have not been set.'))
        frame_url = html_escape(self.get_grafana_auth_url(frame_src))
        frame_layout = '<iframe id="' + frame_id + '" marginwidth="0" ' + \
            'marginheight="0" frameborder="no"' + \
            frame_params + ' src="' + frame_url + '"></iframe>'
        grafana_frame = frame_layout
        return grafana_frame
