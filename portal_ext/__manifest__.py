# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Portal Extended",
    "summary": "Modify and extend Portal module",
    "version": '10.0.1.1.0',
    "category": "Tools",
    "website": "http://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "depends": [
        'portal',
    ],
    "data": [
        'data/res_config_settings_data.xml',
        'wizard/portal_wizard_views.xml',
        'views/base_config_settings.xml',
    ],
    "installable": True,
    "application": False,
}
