# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Base Report Odd Even Pages',
    'summary': 'Functionality to modify report generated ensuring and odd or \
        even number of pages.',
    'version': '16.0.1.0.0',
    'category': 'Tools',
    'website': 'https://moval.es',
    'author': 'Moval Agroingeniería',
    'license': 'AGPL-3',
    'application': False,
    'installable': True,
    'price': 5.0,
    'currency': 'EUR',
    'images': [
        'static/description/banner.png'
    ],
    'depends': [
        'base',
    ],
    'data': [
        'views/ir_actions_views.xml',
    ],
}
