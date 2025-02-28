# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name": "Task Timer",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "version": "16.0.1",
    "category": "Project",
    "summary": "task timer, manage task time app, countdown timer module, calculate task start time, calculate work stop time, manage work time duration, time report timer,calculate work time,calculate task time odoo",
    "description": """This module allows the user to start/stop the time of a task. Easy to calculate the duration of time taken for the task.""",

    "depends": [
        'project',
        'hr_timesheet',
        'analytic'
    ],
    "data": [
        'security/task_time_security.xml',
        'security/ir.model.access.csv',
        'views/res_config_setting.xml',
        'views/project_task_time.xml',
    ],
    'assets': {
        'web.assets_common': [
            'sh_task_time/static/src/scss/time_track.scss'
        ],
    },
    "images": ["static/description/background.png", ],
    "license": "OPL-1",
    "installable": True,
    "auto_install": False,
    "application": True,
    "price": "9",
    "currency": "EUR"
}
