# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "RemoteControl: Netilion",
    "summary": "Netilion Connect REST API actions and MDM sensor readings",
    "version": "10.0.1.0.1",
    "category": "Tools",
    "author": "Moval Agroingeniería",
    "website": "https://www.moval.es",
    "license": "AGPL-3",
    "depends": [
        "base_remotecontrol",
        "mdm_sensor_management_remotecontrol",
    ],
    "data": [
        "data/data.xml",
    ],
    "uninstall_hook": "uninstall_hook",
    "installable": True,
    "application": False,
}