# Copyright 2023-2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0.html).

{
    "name": "Display Decimal Precision",
    "summary": "Separate computation precision from display precision",
    "version": "18.0.3.0.0",
    "category": "Hidden/Dependency",
    "website": "https://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "depends": [
        "base",
        "mail",
        "product",
        "sale",
        "sale_stock",
        "stock",
    ],
    "data": [
        "views/decimal_precision_view.xml",
        "views/res_currency_view.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
}
