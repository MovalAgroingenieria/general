# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    'name': 'Appointment Google Meet Integration',
    'summary': 'Integration between appointments and Google Meet',
    'version': '16.0.1.0.0',
    'author': 'Moval Agroingeniería',
    'website': 'https://moval.es',
    'license': 'AGPL-3',
    'category': 'Website/Website',
    'application': False,
    'installable': True,
    'auto_install': False,
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
}
