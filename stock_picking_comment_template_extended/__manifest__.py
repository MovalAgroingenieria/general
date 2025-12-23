# Copyright 2025 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Picking Comments Extended",
    "summary": "Extend stock picking comment templates with pre-rendered top and bottom comments",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "Moval Agroingeniería",
    "maintainers": ["Moval Agroingeniería"],
    "website": "https://www.moval.es",
    "category": "Inventory/Warehouse",
    "depends": [
        "stock_picking_comment_template",
    ],
    "data": [
        "views/stock_picking_view.xml",
        "reports/report_picking.xml",
        "reports/report_delivery_document.xml",
    ],
    "installable": True,
    "application": False,
}
