# -*- coding: utf-8 -*-
# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Account Payment Partner Extended',
    'summary': """Extend the functionality of parent module""",
    "version": "15.0.1.0.0",
    "category": "Moval General Addons",
    "website": "http://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "depends": [
        "account_payment_partner",
    ],
    "data": [
        "views/res_partner_view.xml",
    ],
    "installable": True,
    "application": False,
}
