# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    'name': 'Role Management',
    'summary': 'Track and edit employee roles',
    'version': "17.0.1.0.0",
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
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/res_users_view.xml',
        'views/hr_role_assignment_view.xml',
        'views/hr_role_view.xml',
        'views/hr_level_view.xml',
        'views/hr_role_menus.xml',
        'views/hr_employee_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_role_management/static/src/css/hr_role_management.css',
        ],
    },
}
