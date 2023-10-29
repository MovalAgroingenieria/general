# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    'name': 'Localization Management',
    'summary': 'Localization based on a hierarchy of territories '
               '(regions, provinces and municipalities)',
    'version': '16.0.1.0.0',
    'author': 'Moval Agroingeniería',
    'license': 'AGPL-3',
    'category': 'Hidden',
    'application': False,
    'installable': True,
    'depends': [
        'base_gen',
    ],
    'data': [
        'views/res_region_views.xml',
        'views/res_province_views.xml',
        'views/res_municipality_views.xml',
        'views/res_place_views.xml',],
    'assets': {
        'web.assets_backend': [
            'base_loc/static/src/css/base_loc.css',
        ],
    },
}