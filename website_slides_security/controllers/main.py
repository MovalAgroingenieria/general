# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import http
from odoo.http import request
from odoo.addons.website_slides.controllers.main import WebsiteSlides


class WebsiteSlidesSecurityMiddleware(http.Controller):
    """Middleware to intercept slide comment requests and enforce authentication"""

    @http.route([
        '/slides/slide/<int:slide_id>/comment/secure'
    ], type='http', auth="user", methods=['POST'], website=True, csrf=False)
    def secure_slide_comment(self, slide_id, **post):
        """Secure endpoint that requires authentication for slide comments"""
        # Get the slide
        slide = request.env['slide.slide'].browse(slide_id)
        if not slide.exists() or not slide.channel_id.can_see:
            return request.not_found()

        # Call the original controller method
        original_controller = WebsiteSlides()
        return original_controller.slide_comment(slide, **post)

    @http.route([
        '/slides/slide/<int:slide_id>/comment'
    ], type='http', auth="public", methods=['POST'], website=True)
    def intercept_slide_comment(self, slide_id, **post):
        """Intercept public comment attempts and redirect to login"""
        if not request.env.user or request.env.user._is_public():
            # Redirect to login with return URL
            return request.redirect('/web/login?redirect=/slides/slide/%s' % slide_id)

        # If user is authenticated, proceed with original method
        slide = request.env['slide.slide'].browse(slide_id)
        if not slide.exists() or not slide.channel_id.can_see:
            return request.not_found()

        original_controller = WebsiteSlides()
        return original_controller.slide_comment(slide, **post)
