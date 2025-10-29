# -*- coding: utf-8 -*-
# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Odoo Mobile App",
    "summary": "Mobile App to connect with Odoo",
    "version": '10.0.1.0.0',
    "category": "Mobile",
    "website": "http://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "depends": [
        'mail',
        'portal_ext',
    ],
    "data": [
        "security/oma_security.xml",
        "security/ir.model.access.csv",
        "data/oma_config_settings_data.xml",
        "views/ir_model_view.xml",
        "views/ir_module_module_view.xml",
        "views/oma_token_view.xml",
        "views/oma_config_settings_view.xml",
        "views/oma_notification_view.xml",
        "views/oma_notification_event_view.xml",
        "views/oma_notification_set_view.xml",
        "views/oma_menus.xml",
    ],
    "installable": True,
    "application": True,
}
