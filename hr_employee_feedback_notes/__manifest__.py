# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Employee Feedback Notes',
    'version': '16.0.1.0.0',
    'summary': 'Private feedback notes linked to employees',
    'author': 'Moval Agroingeniería',
    'category': 'Human Resources',
    'depends': ['hr'],
    'data': [
        'security/feedback_security.xml',
        'security/ir.model.access.csv',
        'views/hr_feedback_note_views.xml',
        'views/hr_feedback_note_menu.xml',
        'views/hr_employee_views.xml',
        'views/hr_employee_feedback_note_type_views.xml'
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
