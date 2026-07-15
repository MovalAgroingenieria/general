# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Moval External Apps Authentication',
    'version': '10.0.1.1.0',
    'summary': 'Authentication framework for external Moval apps embedded '
               'in Odoo',
    'author': 'Moval Agroingeniería',
    'website': 'https://www.moval.es',
    'license': 'AGPL-3',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/moval_external_app_views.xml',
        'views/moval_auth_config_views.xml',
        'views/assets.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
