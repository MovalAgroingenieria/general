# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import werkzeug.exceptions
import werkzeug.utils

from odoo import http
from odoo.http import request


class BoardGrafanaController(http.Controller):

    @http.route('/board_grafana/auth', type='http', auth='user')
    def board_grafana_auth(self, path=None, **kwargs):
        grafana_model = request.env['board.grafana']
        # Follows the module ACLs, so portal users never get a token
        if not grafana_model.check_access_rights(
                'read', raise_exception=False):
            raise werkzeug.exceptions.Forbidden()
        url = grafana_model._get_grafana_signed_url(path)
        if not url:
            raise werkzeug.exceptions.NotFound()
        response = werkzeug.utils.redirect(url, 303)
        response.headers['Cache-Control'] = 'no-store'
        return response
