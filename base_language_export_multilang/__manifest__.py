# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Base Language Export Multi-Language",
    "summary": "Override the translation export wizard to allow selecting "
               "all loaded languages for a target module.",
    "version": "10.0.1.0.0",
    "category": "Tools",
    "website": "http://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "depends": [
        "base",
    ],
    "data": [
        "views/base_language_export_views.xml",
    ],
    "application": False,
    "installable": True,
}
