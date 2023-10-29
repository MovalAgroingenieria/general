# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Account Comments Extended",
    "summary": "Extends the functionality of the parent module",
    "version": "16.0.0.0.1",
    "license": "AGPL-3",
    "author": "Moval Agroingeniería",
    "website": "http://www.moval.es",
    "category": "Reporting",
    "application": False,
    "installable": True,
    "depends": [
        "account_comment_template",
    ],
    "data": [
        "views/account_move_view.xml",
        "reports/report_invoice.xml",
    ],
}
