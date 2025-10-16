# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Board Grafana Integration",
    "summary": "Grafana integration for board module",
    "version": '10.0.1.1.1',
    "category": "Moval General Addons",
    "website": "http://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "depends": [
        "board",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/board_grafana_config_settings_view.xml",
        "views/board_grafana_view.xml",
        "views/base_menu.xml",
        "views/resources.xml",
        "views/board_grafana_dashboard_storage_view.xml",
        "data/welcome_grafana_dashboard.xml",
    ],
    "installable": True,
    "application": False,
}
