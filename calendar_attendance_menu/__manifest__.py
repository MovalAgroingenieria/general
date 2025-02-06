# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Calendar Attendance Menu',
    'summary': 'Monitoring global resources attendances',
    'version': '16.0.1.1.0',
    'category': 'Human Resources',
    'website': 'https://www.moval.es',
    'author': 'Moval Agroingeniería',
    'license': 'AGPL-3',
    'depends': [
        'resource',
    ],
    'data': [
        'views/resource_calendar_attendance_view.xml',
    ],
    'application': True,
    'installable': True,
}
