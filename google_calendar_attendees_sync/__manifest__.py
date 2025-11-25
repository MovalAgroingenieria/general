{
    'name': 'Google Calendar Attendees Sync',
    'version': "17.0.1.0.0",
    'category': 'Productivity',
    'summary': 'Sync Odoo events in Google Calendar for all attendees',
    'description': '''
        This module extends Google Calendar functionality to synchronize
        events not only with the organizer, but also with all attendees
        who have Google Calendar configured.

        Features:
        * Automatic synchronization for all attendees
        * Automatic Google Calendar invitation sending
        * Cron job for periodic synchronization
        * Individual user configuration
    ''',
    'author': 'Moval Development',
    'website': 'https://www.moval.com',
    'depends_old': [
        'base',
        'calendar',
        'google_calendar',
    ],
    'data_old': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/calendar_event_views.xml',
        'views/res_users_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}