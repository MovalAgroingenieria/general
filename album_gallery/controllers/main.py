# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import http
from odoo.http import request


class AlbumGalleryController(http.Controller):

    @http.route([
        '/gallery',
    ], type='http', auth="public", method="post", website=True, csrf=False)
    def album_gallery(self, **post):
        return request.render("album_gallery.album_gallery_form", {})
