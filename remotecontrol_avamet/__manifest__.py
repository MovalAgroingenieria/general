# -*- coding: utf-8 -*-
# 2026 Moval Agroingenieria
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "RemoteControl: AVAMET",
    "summary": "Remotecontrol AVAMET (WeatherLink v2)",
    "version": "10.0.1.0.0",
    "category": "Tools",
    "author": "Moval Agroingenieria",
    "website": "http://www.moval.es",
    "license": "AGPL-3",
    "depends": [
        "base_remotecontrol",
        "mdm_sensor_management_remotecontrol",
    ],
    "data": [
        "data/data.xml",
        "views/resources.xml",
        "wizard/avamet_import_wizard_view.xml",
        "views/remotecontrol_view.xml",
    ],
    "qweb": [
        "static/src/xml/avamet_import.xml",
    ],
    "uninstall_hook": "uninstall_hook",
    "installable": True,
    "application": False,
}
