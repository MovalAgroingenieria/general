# -*- coding: utf-8 -*-
# 2022 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    "name": "Timesheet Attendances Project Exclusion",
    "summary": "Exclude the Internal Project in the hours count",
    "version": "16.0.1.0.0",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "category": "Human Resources/Attendances",
    "depends": [
        "hr_timesheet_attendance",
        "project",
    ],
    "data": [
        "views/project_view.xml",
    ],
    "images":  ["static/description/banner.png"],
    "installable": True,
    "application": False,
}
