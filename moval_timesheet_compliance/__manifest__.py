# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0).
{
    "name": "Timesheet Compliance Daily",
    "summary": (
        "Daily timesheet compliance: attendance vs timesheets, telework, "
        "and generic allocation quality."
    ),
    "version": "16.0.1.10.0",
    "category": "Human Resources",
    "license": "AGPL-3",
    "author": "Moval Agroingeniería",
    "website": "https://moval.es",
    "development_status": "Production/Stable",
    "depends": [
        "analytic",
        "hr",
        "hr_attendance",
        "hr_timesheet",
        "hr_telework_tracking_site_capacity",
        "mail",
        "project",
    ],
    "data": [
        "security/security_res_groups.xml",
        "security/security_ir_rule.xml",
        "security/ir.model.access.csv",
        "data/mail_template.xml",
        "data/ir_cron.xml",
        "views/hr_department_views.xml",
        "views/hr_employee_views.xml",
        "views/res_config_settings_views.xml",
        "views/timesheet_compliance_views.xml",
        "views/timesheet_compliance_actions.xml",
        "views/account_analytic_line_actions.xml",
        "views/timesheet_compliance_menus.xml",
    ],
}
