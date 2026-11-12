# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Board Grafana Integration",
    "summary": "Grafana integration for board module",
    "version": '10.0.1.2.0',
    "category": "Moval General Addons",
    "website": "http://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "depends": [
        "board",
    ],
    "external_dependencies": {
        "python": [
            "cryptography",
            "requests",
        ],
    },
    "data": [
        "security/ir.model.access.csv",
        "views/board_grafana_config_settings_view.xml",
        "views/board_grafana_view.xml",
        "views/base_menu.xml",
        "views/resources.xml",
        "views/webclient_templates.xml",
        "views/board_grafana_dashboard_storage_view.xml",
        "data/welcome_grafana_dashboard.xml",
    ],
    "qweb": [
        "static/src/xml/board_grafana_panel.xml",
        "static/src/xml/board_grafana_kiosk.xml",
    ],
    "installable": True,
    "application": False,
}
