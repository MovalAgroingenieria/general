# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "HR Holidays Public Extended",
    "version": "16.0.2.0.9",
    "license": "AGPL-3",
    "category": "Human Resources",
    "website": "https://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "hr_holidays_public",
        "hr_expense",
        "hr_attendance_reason",
        "hr_attendance_report_theoretical_time",
    ],
    "data": [
    ],
    "post_load": "post_load",
    "post_init_hook": "post_init_hook",
    "assets": {
    },
}
