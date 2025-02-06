# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    "name": "Fleet Vehicle Odometer",
    "summary": "Add init value and project in odometer",
    "version": "16.0.1.0.0",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "category": "Human Resources/Attendances",
    "depends": [
        'project',
        'fleet',
    ],
    "data": [
        'views/fleet_vehicle_views.xml',
        'security/fleet_security.xml',
    ],
    "installable": True,
    "application": False,
}
