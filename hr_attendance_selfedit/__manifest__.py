# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    'name': 'Attendances Self Edit',
    'summary': 'Track and edit employee attendance',
    'version': '16.0.1.0.0',
    'author': 'Moval Agroingeniería',
    'license': 'AGPL-3',
    'category': 'Human Resources/Attendances',
    'application': False,
    'installable': True,
    'depends': [
        'hr_attendance',
    ],
    'data': [
        'views/hr_attendance_view.xml',
        'views/custom_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_attendance_selfedit/static/src/css/hr_attendance_selfedit.css',
        ],
    },
}
