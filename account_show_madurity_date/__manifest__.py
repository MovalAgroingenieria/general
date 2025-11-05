# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Account Show Madurity Date',
    'summary': 'Show madurity date by default',
    'version': '16.0.1.0.0',
    'category': 'Moval General Addons',
    'website': 'http://www.moval.es',
    'author': 'Moval Agroingeniería',
    'license': 'AGPL-3',
    'installable': True,
    'application': False,
    'depends': [
        'account',
    ],
    'data': [
        'views/account_move_views.xml',
    ],
}
