# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    "name": "DECA - Stock",
    "summary": "Prepare and print DECA transport documents from stock pickings",
    "version": "18.0.1.0.1",
    "category": "Localization/Spain",
    "website": "https://www.moval.es",
    "author": "Moval Agroingeniería",
    "maintainers": ["Moval Agroingeniería"],
    "license": "AGPL-3",
    "depends": [
        "base_location",
        "l10n_es_deca",
        "stock",
    ],
    "data": [
        "security/deca_stock_security.xml",
        "security/ir.model.access.csv",
        "report/deca_delivery_report.xml",
        "wizards/deca_new_confirm_views.xml",
        "views/stock_picking_views.xml",
        "views/deca_stock_menus.xml",
    ],
}
