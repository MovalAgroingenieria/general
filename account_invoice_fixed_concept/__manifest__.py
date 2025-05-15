# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    "name": "Account Invoice Fixed Concept",
    "summary": "Adds a new invoice report with a fixed concept.",
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
        "views/account_move_fixed_concept_views.xml",
        "views/account_move_views.xml",
        "reports/report_invoice.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "account_invoice_fixed_concept/static/src/css/"
            "account_invoice_fixed_concept.css",
        ],
    },
}
