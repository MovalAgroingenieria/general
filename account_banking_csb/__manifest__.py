# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Account Banking CSB Direct Debit",
    "summary": "Create CSB files for Direct Debit",
    "version": "16.0.0.0.1",
    "license": "AGPL-3",
    "author": "Moval Agroingeniería",
    "website": "http://www.moval.es",
    "category": "Banking addons",
    "application": False,
    "installable": True,
    "post_init_hook": "update_bank_journals",
    "depends": [
        "account_banking_pain_base"
    ],
    "data": [
        "data/account_payment_method.xml",
        "security/ir.model.access.csv",
    ],
}
