# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'SMS WauSMS',
    'summary': 'SMS Text Messaging',
    'version': '16.0.0.0.0',
    'category': 'Tools',
    'website': 'https://www.moval.es',
    'author': 'Moval Agroingeniería',
    'license': 'AGPL-3',
    'application': False,
    'installable': True,
    'depends': [
        'sms_alternatives',
        'sms',
    ],
    'data': [
        'views/res_config_settings_views.xml',
        'views/sms_sms_views.xml',
    ],
}
