# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    'name': 'Attendances Fix for lastnames',
    'summary': 'Add fields of lastnames to Employee to avoid errors',
    'version': '16.0.1.0.0',
    'author': 'Moval Agroingeniería',
    'license': 'AGPL-3',
    'category': 'Human Resources/Attendances',
    'application': False,
    'installable': True,
    'depends': [
        'hr_attendance',
        'hr_employee_lastnames',
    ],
    'data': [
    ],
}
