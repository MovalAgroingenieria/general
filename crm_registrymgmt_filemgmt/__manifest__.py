# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Entry Registry and File Management',
    'summary': 'Tracking for entry registries and file management relation',
    'version': "17.0.1.0.0",
    'category': 'Customer Relationship Management',
    'website': 'https://odoo-community.org/',
    'author': 'Moval Agroingeniería',
    'license': 'AGPL-3',
    'depends_old': [
        'crm_filemgmt',
        'crm_registrymgmt',
    ],
    'data_old': [
        'views/res_registry_view.xml',
        'views/res_file_views.xml',
        'reports/res_registry_report.xml',
    ],
    'application': False,
    'installable': True,
}
