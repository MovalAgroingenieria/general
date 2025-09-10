# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Account Analytic Distribution Simple',
    'version': '16.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Simple analytic distribution as many2one field',
    'description': """
        This module replaces the complex analytic distribution widget with a
        simple many2one field that allows selecting any analytic account
        directly. The selected account is automatically assigned 100%.

        Currently supported:
        - Account Move Lines (invoice lines, journal entries)
    """,
    'author': 'Moval',
    'website': 'https://www.moval.es',
    'license': 'AGPL-3',
    'depends': ['account', 'analytic', 'account_reconcile_oca'],
    'auto_install': False,
    'application': False,
    'sequence': 1000,
    'data': [
        'views/account_move_views.xml',
        'views/account_bank_statement_line_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
