# -*- coding: utf-8 -*-
# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "QWeb Financial Reports: Add GroupBy in Account Type",
    "summary": "OCA Financial Reports Add Filter for Group By",
    "version": "14.0.1.1.0",
    "category": "Moval General Addons",
    "website": "http://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "depends": [
        "account_financial_report",
        "account",
    ],
    "data": [
        "views/account_views.xml",
        "wizard/trial_balance_wizard_view.xml",
        "security/ir.model.access.csv",
        "report/general_ledger_balance.xml",
    ],
    "installable": True,
    "application": False,
}
