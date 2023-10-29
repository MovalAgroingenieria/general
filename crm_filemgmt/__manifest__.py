# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'File Management',
    'summary': 'Monitoring and file relationships',
    'version': '16.0.1.0.0',
    'category': 'Customer Relationship Management',
    'website': 'https://www.moval.es',
    'author': 'Moval Agroingeniería',
    'license': 'AGPL-3',
    'application': True,
    'installable': True,
    'post_init_hook': 'post_init_hook',
    'depends': [
        'base_gen',
        'mail',
    ],
    'data': [
        'data/ir_module_category_data.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/crm_filemgmt_menus.xml',
        'views/res_config_settings_views.xml',
        'views/res_file_views.xml',
        'views/res_filetag_views.xml',
        'views/res_file_category_views.xml',
        'views/res_partner_views.xml',
        'views/res_file_location_views.xml',
        'views/res_file_container_views.xml',
        'views/res_file_containertype_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'crm_filemgmt/static/src/css/crm_filemgmt.css',
            'crm_filemgmt/static/src/iconset/css/filemgmt_iconset.css',
        ],
        'web.report_assets_common': [
            'crm_filemgmt/static/src/iconset/css/filemgmt_iconset.css',
        ],
    },
}
