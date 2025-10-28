# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    'name': 'Biyectiva Moval Chatbot',
    'summary': 'Chatbot security groups for KPI and Token management',
    'version': '16.0.1.0.0',
    'category': 'Hidden',
    'website': 'https://www.moval.es',
    'author': 'Moval Agroingeniería',
    'license': 'AGPL-3',
    'application': False,
    'installable': True,
    'depends': [
        'base',
    ],
    'data': [
        'security/chatbot_groups.xml',
        'security/ir.model.access.csv',
    ],
}
