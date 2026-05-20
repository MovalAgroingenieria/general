# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class WebsiteMenu(models.Model):
    _inherit = "website.menu"

    @api.model
    def _moval_remove_default_optional_menus(self):
        """Remove menu entries auto-created by optional dependencies.

        ``website_blog`` and ``website_slides`` ship their own top-level
        menu entries with ``noupdate=1``. They are recreated every time
        those modules are (re)installed/updated. We replace them with our
        own entries (Noticias, Zona Regantes) and want to keep them gone
        after any update.
        """
        xmlids = (
            "website_blog.menu_news",
            "website_slides.website_menu_slides",
        )
        for xmlid in xmlids:
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if menu:
                menu.sudo().unlink()
