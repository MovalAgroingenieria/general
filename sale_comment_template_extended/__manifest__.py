# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Sale Comments Extended",
    "summary": "Extends the functionality of the parent module",
    "version": "17.0.1.0.0",
    "license": "AGPL-3",
    "author": "Moval Agroingeniería",
    "website": "http://www.moval.es",
    "category": "Reporting",
    "application": False,
    "installable": True,
    "depends": [
        "sale_comment_template",
    ],
    "data_old": [
        "views/sale_order_view.xml",
        "reports/report_saleorder.xml",
    ],
}
