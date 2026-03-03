# Copyright 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "External Agent Permissions",
    "version": "18.0.1.0.0",
    "category": "Sales/CRM",
    "summary": (
        "Fine-grained access control for external agents and internal salespeople "
        "in Contacts and CRM"
    ),
    "website": "https://www.moval.es",
    "author": "Moval Agroingeniería S.L.",
    "license": "AGPL-3",
    "depends": [
        "base",
        "contacts",
        "crm",
        "sales_team",
        "sale",
        "commission_oca",
    ],
    "post_init_hook": "post_init_sync_agents",
    "data": [
        "security/external_agent_security.xml",
        "security/ir.model.access.csv",
        "views/res_users_views.xml",
        "wizards/update_agents_wizard_views.xml",
        "views/res_partner_views.xml",
        "views/crm_lead_views.xml",
        "views/crm_menu_access.xml",
    ],
}
