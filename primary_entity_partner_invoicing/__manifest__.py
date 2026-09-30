# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    "name": "Primary Entity Partner Invoicing",
    "summary": "Keep the census primary entity on invoice lines",
    "version": "18.0.1.1.0",
    "category": "Accounting/Accounting",
    "license": "AGPL-3",
    "author": "Moval Agroingeniería",
    "website": "https://www.moval.es",
    "depends": [
        "base_invoicing",
        "base_general_entity_period_census",
    ],
    "data": [
        "views/account_move_views.xml",
        "views/account_move_line_views.xml",
    ],
}
