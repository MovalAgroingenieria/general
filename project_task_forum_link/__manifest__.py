# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    "name": "Project Task Forum Link",
    "summary": "This module adds link between project tasks and forum posts.",
    "version": '16.0.1.1.0',
    "category": "Moval General Addons",
    "website": "http://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "depends": [
        "project",
        "website_forum",
    ],
    "data": [
        'security/ir.model.access.csv',
        'wizards/wizard_create_forum_post_from_task_view.xml',
        'views/project_task_views.xml',
        'views/forum_views.xml',

    ],
    "installable": True,
    "application": False,
}
