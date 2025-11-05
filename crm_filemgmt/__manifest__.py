# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'File Management',
    'summary': 'Documentary management through Files.',
    'version': '16.0.0.0.0',
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
        'base_comment_template',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/res_file_category_data.xml',
        'data/res_file_stage_data.xml',
        'views/crm_filemgmt_menus.xml',
        'views/res_config_settings_views.xml',
        'views/res_file_views.xml',
        'views/res_file_stage_views.xml',
        'views/res_file_category_views.xml',
        'views/res_file_report_views.xml',
        'views/res_file_location_views.xml',
        'views/res_file_container_views.xml',
        'views/res_file_containertype_views.xml',
        'views/res_filetag_views.xml',
        'views/res_partner_views.xml',
        'reports/res_file_report_base.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'crm_filemgmt/static/src/css/crm_filemgmt.css',
            'crm_filemgmt/static/lib/filemgmt_iconset/filemgmt_iconset.css',
        ],
        'web.assets_frontend': [
            'crm_filemgmt/static/lib/filemgmt_iconset/filemgmt_iconset.css',
        ],
        'web.report_assets_common': [
            'crm_filemgmt/static/lib/filemgmt_iconset/filemgmt_iconset.css',
        ],
    },
}
