# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Website Automatic Homepage",
    "summary": "Sets a default homepage with the company name as title.",
    "version": "10.0.1.0.1",
    "category": "Website",
    "website": "http://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "depends": [
        "website",
        "website_blog",
        "website_slides",
        "cim_complaints_channel_website",
    ],
    "data": [
        "data/website_menu_data.xml",
        "views/website_homepage_template.xml",
        "views/website_footer_template.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
}
