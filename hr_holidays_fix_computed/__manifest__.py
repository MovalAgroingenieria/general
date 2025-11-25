# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    "name": "HR Holidays Fix Computed",
    "summary": "Adds number_of_days field to hr.leave form view above number_of_days_display",
    "version": "17.0.1.0.0",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "category": "Human Resources",
    "application": False,
    "installable": True,
    "description": """
        This module extends the HR Leave form view to display the computed
        number_of_days field above the number_of_days_display field for
        better visibility and debugging purposes.
    """,
    "depends_old": [
        "hr_holidays",
        ],
    "data_old": [
        "views/hr_leave_views.xml",
    ],
}