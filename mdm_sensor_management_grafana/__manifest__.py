# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "MDM Sensor Management: Grafana Integration",
    "summary": "Add Dashboard for Measurement Devices and Sensors Management",
    "version": "10.0.1.1.0",
    "category": "Tools",
    "website": "https://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "depends": [
        "board_grafana_integration",
        "mdm_sensor_management",
    ],
    "data": [
        "data/template_multi_sensor_grafana_dashboard.xml",
        "data/template_mono_sensor_grafana_dashboard.xml",
        "data/template_mono_sensor_histogram_grafana_dashboard.xml",
        "views/mdm_menus.xml",
    ],
    "application": False,
    "installable": True,
}
