.. |badge1| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

|badge1|


==============================
Google Calendar Attendees Sync
==============================

**Table of contents**

.. contents::
   :local:


Description
===========

This module extends Google Calendar functionality in Odoo v16 to synchronize events not only with the organizer, but also with all attendees who have Google Calendar configured.

Problem Solved
--------------

In standard Odoo v16, when you create a calendar event with multiple attendees, the event only synchronizes with the **organizer/responsible** user's Google Calendar. Other attendees do not receive the event in their Google calendars, even if they have Google Calendar configured.

Features
========

🎯 Automatic Synchronization for Attendees
-------------------------------------------

- Synchronize events individually in each attendee's Google Calendar
- Each attendee receives the event in their personal calendar
- The event is shown from their perspective (as guest, not as organizer)

📧 Automatic Google Invitations
--------------------------------

- Automatic Google Calendar invitation configuration
- ``sendNotifications: true`` - Send email notifications
- ``sendUpdates: 'all'`` - Notify all attendees
- Attendees receive native Google Calendar invitations

⚙️ User Configuration
----------------------

- ``google_calendar_attendee_sync`` field in user preferences
- Each user can enable/disable automatic synchronization
- Log of synchronized events and errors

🔄 Automatic Synchronization
-----------------------------

- Cron job every 2 hours to synchronize attendee events
- Automatic synchronization when creating/modifying events
- Only synchronizes future and recent events (last 7 days to 90 days)

🎛️ Manual Control
------------------

- "Synchronize Manually" button in event form
- Server action for bulk synchronization
- Connection test buttons in user preferences

Installation
============

1. Place the module in ``addons/moval_addons/general/google_calendar_attendees_sync/``
2. Update applications list
3. Install "Google Calendar Attendees Sync" module

Configuration
=============

For Administrators
------------------

1. Go to **Settings → Users & Companies → Users**
2. For each user, enable "Automatic Attendee Synchronization"

For Users
---------

1. Go to **Preferences → Google Calendar Synchronization**
2. Configure your Google Calendar (if not configured)
3. Enable "Automatic Attendee Synchronization"
4. Use "Test Connection" to verify it works

Usage
=====

Event Creation
--------------

1. Create a calendar event normally
2. Add attendees with ``attendee_ids``
3. Ensure "Sync with Attendees" is enabled
4. The event will automatically synchronize with all attendees

Manual Synchronization
----------------------

- **Individual event**: Use "Synchronize Manually" button
- **Multiple events**: Select events → Actions → "Synchronize with Attendees"
- **For user**: Go to Preferences → "Synchronize My Events"

Added Fields
============

calendar.event
--------------

- ``attendee_sync_enabled``: Enable/disable synchronization for the event
- ``last_attendee_sync``: Date/time of last synchronization
- ``sync_errors``: Synchronization error log

res.users
---------

- ``google_calendar_attendee_sync``: Enable automatic synchronization
- ``google_calendar_sync_errors``: Error log
- ``attendee_events_synced``: Counter of synchronized events

Main Methods
============

CalendarEvent
-------------

- ``_sync_attendees_calendars()``: Synchronize with all attendees
- ``_google_values_for_attendee()``: Generate attendee-specific values
- ``action_sync_attendees()``: Manual synchronization action

ResUsers
--------

- ``_sync_my_attendee_events()``: Synchronize events where I am attendee
- ``action_test_google_calendar_connection()``: Test connection
- ``_cron_sync_attendee_events_all_users()``: Scheduled task

Scheduled Tasks
===============

- **Attendee Synchronization**: Every 2 hours
- **Error Cleanup**: Daily (keeps last 5 errors)

Technical Notes
===============

Google Calendar API Integration
--------------------------------

The module uses existing ``google_calendar`` infrastructure:

- Individual user tokens
- Error handling and timeouts
- Respects Google API limits

Attendee Perspective
--------------------

Events are created in Google Calendar from the attendee's perspective:

- ``organizer.self = False``
- ``attendees[].self = True`` for the attendee
- Appropriate guest permissions

Error Handling
--------------

- Detailed error logging per user
- Odoo notifications for synchronization errors
- Automatic cleanup of old errors

Troubleshooting
===============

Event does not synchronize
---------------------------

1. Verify attendee has Google Calendar configured
2. Check that ``attendee_sync_enabled = True`` in the event
3. Verify that ``google_calendar_attendee_sync = True`` in user
4. Review errors in event's ``sync_errors``

Connection errors
-----------------

1. Use "Test Connection" in user preferences
2. Verify valid Google tokens
3. Check Odoo logs for detailed errors

Credits
=======

Authors
~~~~~~~

* Moval Agroingeniería S.L.

Contributors
~~~~~~~~~~~~

* Guillermo Amante <gamante@moval.es>
* Samuel Fernández <sfernandez@moval.es>
* Alberto Hernández <ahernandez@moval.es>
* Eduardo Iniesta <einiesta@moval.es>
* Jesús Martínez <jmartinez@moval.es>
* Miguel Mora <mmora@moval.es>
* Miguel Ángel Rodríguez <marodriguez@moval.es>
* Juanu Sandoval <jsandoval@moval.es>
* Salvador Sánchez <ssanchez@moval.es>
* Jorge Vera <jvera@moval.es>

Maintainers
~~~~~~~~~~~

This module is maintained by Moval Agroingeniería.

.. image:: https://raw.githubusercontent.com/MovalAgroingenieria/public-assets/master/logos/logo_moval_small.png
   :alt: Moval Agroingeniería
   :target: http://moval.es
