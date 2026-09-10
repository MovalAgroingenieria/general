# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Attendance Big Button",
    "summary": "Provide a kiosk-like big button for employee check in/out",
    "version": "18.0.1.0.0",
    "category": "Human Resources/Attendances",
    "website": "https://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "depends": ["hr_attendance", "hr_attendance_reason"],
    "data": [
        "security/ir.model.access.csv",
        "views/hr_attendance_big_button_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "hr_attendance_big_button/static/src/scss/hr_attendance_big_button.scss",
            "hr_attendance_big_button/static/src/js/attendance_menu.js",
            "hr_attendance_big_button/static/src/xml/attendance_menu.xml",
        ],
    },
}
