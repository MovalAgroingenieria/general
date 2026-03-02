# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Base Remote Control Engine',
    'summary': 'Generic engine to integrate remote controls (REST/SQL) '
               'with actions and procedures',
    'version': '10.0.1.0.1',
    'category': 'Tools',
    "website": "http://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "depends": [
        "base",
        "mail",
        "web_ir_actions_act_window_message",
        "document",
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/base_remotecontrol_menus.xml',
        'views/remotecontrol_views.xml',
    ],
    'installable': True,
    'application': False,
}
