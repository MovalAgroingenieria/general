# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import base64

from odoo import http
from odoo.http import request


class L10nEsDecaController(http.Controller):
    @http.route(
        ["/deca/<string:access_token>"],
        type="http",
        auth="public",
        website=False,
        sitemap=False,
        csrf=False,
    )
    def l10n_es_deca_public_pdf(self, access_token, **kwargs):
        # pylint: disable=unused-argument
        if not access_token:
            return request.not_found()
        version = (
            request.env["deca.version"]
            .sudo()
            .search([("access_token", "=", access_token)], limit=1)
        )
        if not version or not version.pdf_attachment_id:
            return request.not_found()
        pdf_content = base64.b64decode(version.pdf_attachment_id.datas)
        filename = version.pdf_filename or ("DECA-%s.pdf" % version.id)
        headers = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", len(pdf_content)),
            ("Content-Disposition", "inline; filename=%s" % filename),
            ("X-Robots-Tag", "noindex, nofollow"),
        ]
        return request.make_response(pdf_content, headers=headers)
