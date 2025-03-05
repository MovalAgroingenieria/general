# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Entry Registry and File Management',
    'summary': 'Tracking for entry registries and file management relation',
    'version': '16.0.1.1.0',
    'category': 'Customer Relationship Management',
    'website': 'https://odoo-community.org/',
    'author': 'Moval Agroingeniería',
    'license': 'AGPL-3',
    'depends': [
        'crm_filemgmt',
        'crm_registrymgmt',
    ],
    'data': [
        'views/res_registry_view.xml',
        'views/res_file_views.xml',
        'security/ir.model.access.csv',
    ],
    'application': False,
    'installable': True,
}
