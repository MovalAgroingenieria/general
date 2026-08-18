# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Account Modify Payment Batches Communication",
    "summary": "Integration with a complementary application for managing the "
               "modification of payment batches communication.",
    "version": '10.0.1.1.0',
    "category": "Accounting",
    "website": "http://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "depends": [
        "moval_external_apps_iframe",
        "account_payment_order",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_modify_payment_batches_communication_view.xml",
        "views/account_modify_payment_batches_communication_actions.xml",
    ],
    "installable": True,
    "application": False,
    "post_init_hook": "post_init_hook",
}
