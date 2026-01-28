# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Worker Activity Self Monitoring",
    "summary": "Worker will be able to monitor his own activity.",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "Moval Agroingeniería",
    "website": "http://www.moval.es",
    "category": "Human Resources/Attendance",
    "depends": [
        "web",
        "hr_attendance",
        "bus",
        "project",
    ],
    "data": [],
    "assets": {
        "web.assets_backend": [
            "/worker_activity_self_monitoring/static/src/css/tray_icons.css",
            "/worker_activity_self_monitoring/static/src/js/task_systray.js",
            "/worker_activity_self_monitoring/static/src/js/attendance_systray.js",
            "/worker_activity_self_monitoring/static/src/xml/task_systray.xml",
            "/worker_activity_self_monitoring/static/src/xml/attendance_systray.xml",
        ],
    },
    "application": False,
    "installable": True,
    "uninstall_hook": "uninstall_hook",
}
