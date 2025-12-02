# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    'name': 'Biyectiva Moval Chatbot',
    'summary': 'Biyectiva Chatbot Integration for Odoo 16',
    'version': '16.0.2.0.0',
    'category': 'Hidden',
    'website': 'https://www.moval.es',
    'author': 'Moval Agroingeniería',
    'license': 'AGPL-3',
    'application': False,
    'installable': True,
    'depends': [
        'base',
        'mail',
        'project',
        'project_task_reviewer',
        'project_type',
        'hr_timesheet',
    ],
    'data': [
        'security/chatbot_groups.xml',
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/mail_notification_chatbot_views.xml',
    ],
}
