# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import http
from odoo.http import request


PAGES = {
    'politica-cookies': 'website_automatic_homepage.politica_cookies',
    'politica-privacidad': 'website_automatic_homepage.politica_privacidad',
    'aviso-legal': 'website_automatic_homepage.aviso_legal',
}


class WebsiteLegalPages(http.Controller):

    @http.route([
        '/page/politica-cookies',
        '/page/politica-privacidad',
        '/page/aviso-legal',
    ], type='http', auth='public', website=True)
    def legal_page(self, **kw):
        slug = request.httprequest.path.rsplit('/', 1)[-1]
        template = PAGES.get(slug)
        if not template:
            return request.not_found()
        return request.render(template, {'path': slug})
