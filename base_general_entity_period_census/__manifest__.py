# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    "name": "Base General Entity - Period Census",
    "version": "18.0.2.0.0",
    "category": "Base",
    "license": "AGPL-3",
    "author": "Moval Agroingeniería",
    "website": "https://www.moval.es",
    "depends": [
        "base_general_entity",
        "product",
        "uom",
    ],
    "data": [
        "data/decimal_precision_data.xml",
        "security/ir.model.access.csv",
        "views/general_entity_census_views.xml",
        "views/res_partner_views.xml",
        "views/menu_views.xml",
    ],
}
