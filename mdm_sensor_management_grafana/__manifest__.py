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
        "security/ir.model.access.csv",
        "data/template_multi_sensor_grafana_dashboard.xml",
        "data/template_mono_sensor_grafana_dashboard.xml",
        "data/template_mono_sensor_histogram_grafana_dashboard.xml",
        "data/template_element_monosensor_integrated.xml",
        "data/template_element_sensor_integrated_histogram.xml",
        "data/template_element_multisensor_integrated.xml",
        "views/measurement_device_sensor_type_views.xml",
        "views/mdm_menus.xml",
        "wizards/mdm_grafana_panel_wizard_views.xml",
    ],
    "application": False,
    "installable": True,
}
