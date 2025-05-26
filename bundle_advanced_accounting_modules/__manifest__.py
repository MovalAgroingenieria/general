# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    "name": "Bundle advanced accounting modules",
    "summary": "Install at once all modules related to the accounting.",
    "version": "16.0.1.0.0",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "category": "Hidden",
    "application": False,
    "installable": True,
    "depends": [
        "bundle_common_accounting_modules",
        "analytic",
        "mis_builder",
        "mis_builder_budget",
        "payment",
    ],
    "data": [
    ],
}
