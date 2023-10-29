# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Board Grafana Integration',
    'summary': 'Grafana integration for board module',
    'version': '16.0.1.0.0',
    'category': 'Moval General Addons',
    'website': 'http://www.moval.es',
    'author': 'Moval Agroingeniería',
    'license': 'AGPL-3',
    'application': False,
    'installable': True,
    'depends': [
        'board',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_view.xml',
        'views/board_grafana_view.xml',
        'views/base_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'board_grafana_integration/static/src/css/board_grafana_integration.css',
            'board_grafana_integration/static/src/iconset/css/board_grafana_integration_iconset.css',
        ],
        'web.report_assets_common': [
            'board_grafana_integration/static/src/iconset/css/board_grafana_integration_iconset.css'
        ],
    },
}
