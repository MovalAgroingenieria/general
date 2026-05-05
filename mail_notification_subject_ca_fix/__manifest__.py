# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Mail Notification Subject CA Fix',
    'summary': 'Fix broken Catalan translation in Mail subject template',
    'version': '10.0.1.0.0',
    'category': 'Tools',
    'website': 'https://www.moval.es',
    'author': 'Moval Agroingeniería',
    'license': 'AGPL-3',
    'depends': [
        'mail',
    ],
    'data': [],
    'application': False,
    'installable': True,
    'post_init_hook': 'post_init_hook',
}
