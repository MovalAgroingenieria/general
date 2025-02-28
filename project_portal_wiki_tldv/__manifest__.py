# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    "name": "Project Portal Wiki & TLDV Enhancements",
    "summary": "Adds a URL field in projects, displays Wiki pages on the "
               "portal, hides hours for portal users, and integrates TLDV "
               "video downloads into Wiki pages.",
    "version": "16.0.1.0.0",
    "category": "Moval General Addons",
    "website": "http://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "depends": [
        "project",
        "website",
        "portal",
        "document_page_project",
        "document_page_access_group",
    ],
    "data": [
        "security/security.xml",
        'security/ir.model.access.csv',
        "views/project_views.xml",
        "views/portal_templates.xml",
        "views/config_settings_view.xml",
        "views/document_page_views.xml",
        "data/ir_cron.xml",
    ],
    "installable": True,
    "application": False,
}
