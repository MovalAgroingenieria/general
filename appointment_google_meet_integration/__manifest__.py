# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'author': 'Moval Agroingeniería',
    'website': 'https://moval.es',
    'license': 'AGPL-3',
    'depends': [
        'base',
        'calendar',
        'website',
        'appointment_booking_ce',
    ],
    'external_dependencies': {
        'python': [
            'google-auth',
            'google-auth-oauthlib',
            'google-auth-httplib2',
            'google-api-python-client',
        ]
    },
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template.xml',
        'views/res_config_settings_views.xml',
        'views/calendar_booking_views.xml',
        'views/calendar_event_views.xml',
        'views/website_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
