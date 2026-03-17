# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "RemoteControl: Intages",
    "summary": "Telecontrol Intages (BigQuery SQL) with default actions and "
               "procedures for Google BigQuery integration",
    "version": "10.0.1.0.2",
    "category": "Tools",
    "author": "Moval Agroingeniería",
    "website": "http://www.moval.es",
    "license": "AGPL-3",
    "depends": [
        "base_remotecontrol",
    ],
    "data": [
        "data/data.xml",
    ],
    "uninstall_hook": "uninstall_hook",
    "installable": True,
    "application": False,
}