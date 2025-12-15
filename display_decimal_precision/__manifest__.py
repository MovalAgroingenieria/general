# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Display Decimal Precision",
    "summary": "Distinguish computation digits and display digits",
    "version": "18.0.3.0.0",
    "category": "Hidden/Dependency",
    "website": "http://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "depends": ["base", "product", "sale", "stock", "mail", "sale_stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/decimal_precision_view.xml",
        "views/res_config_settings_view.xml",
        "views/res_currency_view.xml",
    ],
    "post_init_hook": "post_init_hook",
}
