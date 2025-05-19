# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    "name": "Account Invoice Single Concept",
    "summary": "Adds a invoice report with a single concept and no details.",
    "version": "16.0.1.0.0",
    "category": "Project Management",
    "website": "http://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "installable": True,
    "application": False,
    "depends": [
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_move_single_concept_views.xml",
        "views/account_move_views.xml",
        "reports/report_invoice.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "account_invoice_single_concept/static/src/css/account_invoice_single_concept.css",
        ],
    },
}
