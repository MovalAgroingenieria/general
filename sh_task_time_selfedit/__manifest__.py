# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    "name": "Task Timer Self Edit",
    "summary": "Track and edit task time",
    "version": "16.0.1.0.0",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "category": "Human Resources/Attendances",
    "depends": [
        'project',
        'hr_timesheet',
        'analytic',
        'hr_timesheet_sheet',
    ],
    "data": [
        'views/project_task_time.xml',
    ],
    "installable": True,
    "application": False,
}
