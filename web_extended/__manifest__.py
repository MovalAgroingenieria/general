# -*- coding: utf-8 -*-
# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Web Extended',
    'summary': 'Extension of the core of the Odoo Web Client',
    'version': '16.0.1.0.0',
    'category': 'Moval General Addons',
    'website': 'http://www.moval.es',
    'author': 'Moval Agroingeniería',
    'license': 'AGPL-3',
    'application': False,
    'installable': True,
    'depends': [
        'web',
    ],
    'data': [
        'views/base_document_layout_views.xml',
        'views/report_templates.xml'
    ],
}
