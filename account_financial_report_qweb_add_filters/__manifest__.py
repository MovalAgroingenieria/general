# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "QWeb Financial Reports: Add GroupBy in Account Type",
    "summary": "OCA Financial Reports Add Filter for Group By",
    "version": "18.0.1.0.0",
    "category": "Moval General Addons",
    "website": "http://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "depends": [
        "web",
        "account_financial_report",
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_views.xml",
        "wizard/trial_balance_wizard_view.xml",
        "views/trial_balance_report_templates.xml",
        "report/general_ledger_balance.xml",
    ],
}
