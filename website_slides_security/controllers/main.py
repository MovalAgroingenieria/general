# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import http
from odoo.addons.website_slides.controllers.main import WebsiteSlides


class WebsiteSlidesSecure(WebsiteSlides):
    """Override website slides controller to add security to comments"""

    @http.route('''/slides/slide/<model("slide.slide", "[('channel_id.can_see', '=', True)]"):slide>/comment''',
                type='http', auth="user", methods=['POST'], website=True)
    def slide_comment(self, slide, **post):
        """Override slide_comment to require user authentication instead of public access.

        This prevents anonymous users from posting spam comments by requiring them
        to be logged in to the system first.
        """
        return super(WebsiteSlidesSecure, self).slide_comment(slide, **post)