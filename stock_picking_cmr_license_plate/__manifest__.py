# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    "name": "Stock Picking CMR License Plate",
    "summary": "Store CMR license plates in a registry to autocomplete them.",
    "version": "16.0.1.0.0",
    "author": "Moval Agroingeniería",
    "category": "Inventory/Inventory",
    "website": "https://www.moval.es",
    "license": "AGPL-3",
    "depends": [
        "stock_picking_cmr_report",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/cmr_license_plate_views.xml",
        "views/stock_picking_views.xml",
        "report/stock_picking_cmr_report.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
}
