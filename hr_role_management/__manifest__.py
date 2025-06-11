# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    'name': 'Role Management',
    'summary': 'Track and edit employee roles',
    'version': '16.0.1.0.0',
    'author': 'Moval Agroingeniería',
    'license': 'AGPL-3',
    'category': 'Human Resources/Attendances',
    'application': False,
    'installable': True,
    'depends': [
        'hr',
        'mail',
    ],
    'data': [
        'views/hr_role_assignment_view.xml',
        'views/hr_role_view.xml',
        'views/hr_role_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_role_management/static/src/css/hr_role_management.css',
        ],
    },
}
