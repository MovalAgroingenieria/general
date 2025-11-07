# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    "name": "Telework and Site Capacity Tracking",
    "summary": "Daily work mode declaration and department capacity "
               "control",
    "version": "16.0.1.4.2",
    "author": "Moval Agroingeniería",
    "maintainers": ["MovalAgroingenieria"],
    "website": "https://moval.es",
    "license": "AGPL-3",
    "category": "Human Resources",
    "depends": [
        "hr",
        "hr_holidays",
        "hr_timesheet",
        "hr_timesheet_sheet",
        "mail",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/telework_bot.xml",
        "data/ir_cron.xml",
        "views/weekly_declaration_views.xml",
        "views/telework_day_views.xml",
        "views/department_views.xml",
        "views/hr_employee_views.xml",
        "views/office_views.xml",
        "views/workstation_views.xml",
        "views/bulk_preferences_views.xml",
        "views/telework_report_wizard_views.xml",
        "views/res_config_settings_views.xml",
        "views/account_analytic_line_views.xml",
        "views/hr_timesheet_sheet_views.xml",
        "views/menu.xml",
        "reports/telework_report.xml",
    ],
    "assets": {
        "web.assets_backend": [
            ("hr_telework_tracking_site_capacity/static/src/js/"
             "telework_mode_field.js"),
            ("hr_telework_tracking_site_capacity/static/src/css/"
             "telework_groups.css"),
            ("hr_telework_tracking_site_capacity/static/src/css/"
             "telework_icons.css"),
            ("hr_telework_tracking_site_capacity/static/src/xml/"
             "telework_mode_field.xml"),
        ],
    },
    "application": False,
    "installable": True,
    "auto_install": False,
}
