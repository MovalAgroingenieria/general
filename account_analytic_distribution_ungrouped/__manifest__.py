# 2025 Moval Agroingeniería
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
        - Account Bank Statement Lines (reconciliation)
        - Sale Orders (analytic_account_id field)
        - Sale Order Lines (analytic_distribution field)
        - Purchase Order Lines (analytic_distribution field)
        - Project Projects (analytic_account_id field)
        - Project Tasks (analytic_account_id field)
        - Account Analytic Lines (account_id field)
        - Contract Lines (analytic_distribution field) - recurring invoices
        - HR Expenses (analytic_distribution field)
        - Account Assets (analytic_distribution field) - asset management
    """,
    'author': 'Moval',
    'website': 'https://www.moval.es',
    'license': 'AGPL-3',
    'depends': [
        'account', 'analytic', 'account_reconcile_oca', 'sale',
        'purchase', 'project', 'contract', 'hr_expense',
        'account_asset_management'
    ],
    'auto_install': False,
    'application': False,
    'sequence': 1000,
    'data': [
        'views/account_move_views.xml',
        'views/account_bank_statement_line_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/project_views.xml',
        'views/account_analytic_views.xml',
        'views/contract_views.xml',
        'views/hr_expense_views.xml',
        'views/account_asset_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
