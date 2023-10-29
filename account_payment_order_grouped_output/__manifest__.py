# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Account Payment Order - Generate grouped moves',
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'Moval Agroingeniería',
    'website': 'http://www.moval.es',
    'category': 'Banking addons',
    'application': False,
    'installable': True,
    'depends': [
        'account_payment_order',
    ],
    'data': [
        'views/account_payment_mode_views.xml',
        'views/account_payment_order_views.xml',
    ],
}
