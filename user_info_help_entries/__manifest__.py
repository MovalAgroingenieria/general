# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'User Info Help Entries',
    'summary': 'Shortcut configuration for other services',
    'version': '16.0.1.0.0',
    'category': 'Moval General Addons',
    'website': 'http://www.moval.es',
    'author': 'Moval Agroingeniería',
    'license': 'AGPL-3',
    'depends': [
        "web",
    ],
    'data': [
        "security/ir.model.access.csv",
        "views/help_entry_views.xml",
        # "views/resources.xml",
        'data/shortcut_definitions.xml',
    ],
    'assets': {
        'web.assets_backend': [
            '/user_info_help_entries/static/src/js/help_entry.js',
        ],
    },
    'installable': True,
    'application': False,
}
