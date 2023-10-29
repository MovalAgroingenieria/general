# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Fontawesome OGMAR',
    'summary': 'Add custom fontawesome fonts for OGMAR',
    'version': '16.0.1.0.0',
    'category': 'Moval General Addons',
    'website': 'http://www.moval.es',
    'author': 'Moval Agroingeniería',
    'license': 'AGPL-3',
    'application': False,
    'installable': True,
    'depends': [
        'web',
    ],
    'data': [
    ],
    'assets': {
        'web.assets_common': [
            'fontawesome_ogmar/static/lib/ogmar_iconset/ogmar_iconset.css',
        ],
    },
}
