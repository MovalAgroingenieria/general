# -*- coding: utf-8 -*-
# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    'name': 'Portal Web Cliente My Details Add Extra Fields',
    'summary': 'Add some extra fields on Portal User My Details Web View',
    'version': '16.0.1.0.0',
    'category': 'Web',
    'website': 'https://www.moval.es',
    'author': 'Moval Agroingeniería',
    'license': 'AGPL-3',
    'application': False,
    'installable': True,
    'depends': [
        'portal',
    ],
    'data': [
        'views/portal_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'views/assets.xml',
        ]
    },
}
