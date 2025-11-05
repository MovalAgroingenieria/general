# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Display Decimal Precision',
    'summary': 'Distinguish computation digits and display digits',
    'version': '16.0.1.0.0',
    'category': 'Hidden/Dependency',
    'website': 'http://www.moval.es',
    'author': 'Moval Agroingeniería',
    'license': 'AGPL-3',
    'depends': [
        'base',
        'product',
        'sale',
        'stock',
        'mail',
    ],
    'data': [
        'views/decimal_precision_view.xml',
        # 'views/res_currency_view.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
}
