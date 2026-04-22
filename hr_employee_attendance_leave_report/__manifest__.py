# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Employee Attendances / Leaves Report",
    "summary": "Create a employee attendance/leaves report",
    "version": "18.0.1.4.0",
    "category": "Moval General Addons",
    "website": "https://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "depends": [
        "hr_attendance",
        "hr_holidays",
        "hr_holidays_public",
        "calendar_public_holiday",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/hr_employee_attendance_leave_wizard_views.xml",
        "report/hr_employee_attendance_leave_report_data.xml",
        "report/hr_employee_attendance_leave_report_templates.xml",
    ],
    "assets": {
        "web.report_assets_common": [
            "hr_employee_attendance_leave_report/static/src/scss/style.scss",
        ],
    },
}
