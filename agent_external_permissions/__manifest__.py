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
    "description": """
This module introduces a clear separation of access rules between
external agents and internal salespeople in Odoo.

External Agents
---------------
* Can only access contacts where they are assigned as external agents
* Can only access CRM opportunities linked to those contacts
* Have no access to Sales Orders

Internal Salespeople
--------------------
* Can only access their own CRM opportunities
* Are not restricted on Sales Orders (standard Odoo behavior applies)

Additional Features
-------------------
* External agents are assigned at contact level
* Agent assignments can be propagated to existing opportunities
* Includes a wizard to synchronize agents on CRM opportunities
* Designed to be compatible with standard Odoo Sales and CRM workflows

This module does not alter standard Sales permissions for internal users.
""",
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
    "data": [
        "security/external_agent_security.xml",
        "security/ir.model.access.csv",
        "views/res_users_views.xml",
        "wizards/update_agents_wizard_views.xml",
        "views/res_partner_views.xml",
        "views/crm_lead_views.xml",
        "views/crm_menu_access.xml",
    ],
    "installable": True,
    "application": False,
}
