# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Moval Corporate Image',
    'summary': 'Decorate instance with Moval logo',
    'version': '16.0.1.1.0',
    'category': 'Moval General Addons',
    'website': 'http://www.moval.es',
    'author': 'Moval Agroingeniería',
    'license': 'AGPL-3',
    'application': False,
    'installable': True,
    'depends': [
        'web_responsive',
        'fontawesome_ext',
    ],
    'data': [
        'views/webclient_templates.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'moval_corporate_image/static/src/components/apps_menu/apps_menu.xml',
        ],
    },
}
