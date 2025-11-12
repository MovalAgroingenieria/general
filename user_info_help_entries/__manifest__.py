# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'User Info Help Entries',
    'summary': 'Shortcut configuration for other services',
    'version': '10.0.1.1.7',
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
        "views/resources.xml",
        'data/shortcut_definitions.xml',
    ],
    'installable': True,
    'application': False,
}
