# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    "name": "Base General Entity",
    "version": "18.0.1.0.0",
    "category": "Base",
    "license": "AGPL-3",
    "author": "Moval Agroingeniería",
    "website": "https://www.moval.es",
    "depends": [
        "base",
        "contacts",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "wizards/partner_entity_type_wizard_views.xml",
        "views/res_partner_views.xml",
        "views/general_entity_member_views.xml",
        "views/menu_views.xml",
    ],
    "application": True,
}
