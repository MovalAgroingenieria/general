# -*- coding: utf-8 -*-
# 2021 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "NRS client SMS",
    "summary": "Send SMS through 360NRS service",
    "version": "10.0.1.2.0",
    "category": "Moval General Addons",
    "website": "http://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "depends": [
        "base",
        "partner_mobile_buttons",
        "account",
    ],
    "data": [
        "views/nrs_config_settings_view.xml",
        "data/nrs_config_settings_data.xml",
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/resources.xml",
        "views/nrs_view.xml",
        "wizards/nrs_wizard_view.xml",
        "views/nrs_tracking_view.xml",
        "views/nrs_template_view.xml",
        "views/res_partner_view.xml",
        "views/account_invoice_view.xml",
        "views/nrs_check_view.xml",
    ],
    "external_dependencies": {
        "python": [
            "phonenumbers",
        ],
    },
    "installable": True,
    "application": False,
    # "price": 10.0,
    # "currency": "EUR",
    # "images": ["static/description/banner.png"],
}
