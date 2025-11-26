# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    'name': 'Appointment Google Meet Integration',
    'summary': 'Integration between appointments and Google Meet',
    'version': "17.0.1.0.0",
    'category': 'Website',
    'website': 'https://www.moval.es',
    'author': 'Moval Agroingeniería',
    'license': 'AGPL-3',
    'application': False,
    'installable': True,
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
    'data_old': [
        'security/ir.model.access.csv',
        'data/mail_template.xml',
        'views/res_config_settings_views.xml',
        'views/calendar_booking_views.xml',
        'views/calendar_event_views.xml',
        'views/website_templates.xml',
    ],
}
