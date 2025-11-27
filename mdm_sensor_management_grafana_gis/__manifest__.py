# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "MDM Sensor Management: Grafana Integration with GIS panels",
    "summary": "Add Dashboard for Measurement Devices for GIS Viewer",
    "version": "10.0.1.1.0",
    "category": "Tools",
    "website": "https://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "depends": [
        "mdm_sensor_management_grafana",
        "mdm_sensor_management_gis",
    ],
    "data": [
        "views/mdm_settings_views.xml",
    ],
    "application": False,
    "installable": True,
}
