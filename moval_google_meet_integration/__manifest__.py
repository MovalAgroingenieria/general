# Copyright 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    'name': 'Google Meet Integration for Appointment Booking',
    'version': '16.0.1.0.0',
    'category': 'Calendar',
    'summary': 'Integrates Google Meet with Zehntech Appointment Booking',
    'description': """
Google Meet Integration for Appointment Booking
==============================================

This module extends the Zehntech Appointment Booking module to generate
Google Meet links automatically using a specific Google account for all
online appointments.

Features:
---------
* Automatic Google Meet link generation for online appointments
* Uses a centralized Google account (movalagroingenieria)
* Integrates with TLDV for automatic meeting recording
* Replaces default Odoo videocall links with Google Meet
* OAuth authentication for secure Google API access
* Configurable per appointment type

The module inherits the existing appointment booking functionality without
modifying the original Zehntech module, ensuring compatibility and easy
maintenance.
    """,
    'author': 'Moval Agroingeniería',
    'website': 'https://moval.es',
    'license': 'AGPL-3',
    'depends': [
        'base',
        'calendar',
        'website',
        'appointment_booking_ce',  # Zehntech module dependency
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
        'views/res_config_settings_views.xml',
        'views/calendar_booking_views.xml',
        'views/calendar_event_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}