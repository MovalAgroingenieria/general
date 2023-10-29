# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Picking Comments Extended",
    "summary": "Extends the functionality of the parent module",
    "version": "16.0.0.0.1",
    "license": "AGPL-3",
    "author": "Moval Agroingeniería",
    "website": "http://www.moval.es",
    "category": "Warehouse Management",
    "application": False,
    "installable": True,
    "depends": [
        "stock_picking_comment_template",
    ],
    "data": [
        "views/stock_picking_view.xml",
        "reports/report_picking.xml",
        "reports/report_delivery_document.xml",
    ],
}
