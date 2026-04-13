# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Base Vote",
    "summary": "Vote types with Jinja2 formulas and votes per partner",
    "version": "18.0.1.0.0",
    "category": "Administration",
    "website": "https://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "development_status": "Production/Stable",
    "depends": ["base", "web"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/vote_type_views.xml",
        "views/partner_vote_views.xml",
        "views/res_partner_views.xml",
    ],
}
