.. |badge1| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

|badge1|


====================================
Appointment Google Meet Integration
====================================

This module extends the **Zehntech Appointment Booking CE** module to automatically generate Google Meet links using a specific Google account for all online appointments.

**Table of contents**

.. contents::
   :local:


Features
========

* Automatic Google Meet link generation for appointments
* Integration with specific corporate account (movalagroingenieria)
* Replaces Odoo video call links with Google Meet
* Configuration per appointment type (enable/disable Google Meet)
* Customizable templates for meeting descriptions
* Secure OAuth authentication
* Does not modify original Zehntech code


Prerequisites
=============

Odoo Modules
~~~~~~~~~~~~

* ``appointment_booking_ce`` (Zehntech) - Must be installed
* ``calendar`` (Odoo core)
* ``website`` (Odoo core)

Python Libraries
~~~~~~~~~~~~~~~~

Install the following libraries in the Odoo virtual environment::

    pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

Google Cloud Console Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Create project in Google Cloud Console**:
   - Go to https://console.cloud.google.com/
   - Create a new project or select an existing one

2. **Enable required APIs**:
   - Google Calendar API
   - Google Meet API (if available)

3. **Create OAuth 2.0 credentials**:
   - Go to "Credentials" → "Create credentials" → "OAuth 2.0 Client ID"
   - Application type: "Web application"
   - Authorized redirect URIs: ``https://your-domain.com/google_meet/oauth/callback``

4. **Get Client ID and Client Secret**


Installation
============

Install the module
~~~~~~~~~~~~~~~~~~

1. Copy the module to the addons folder: ``/path/to/odoo/addons/appointment_google_meet_integration/``
2. Update the application list in Odoo
3. Search and install "Appointment Google Meet Integration"

Configure Google Meet
~~~~~~~~~~~~~~~~~~~~~

1. **Go to Settings → General Settings**
2. **Look for "Google Meet Integration" section**
3. **Enable "Enable Google Meet Integration"**
4. **Complete the fields**:
   - **Google Account Email**: ``movalagroingenieria@gmail.com``
   - **Client ID**: The Client ID from Google Cloud Console
   - **Client Secret**: The Client Secret from Google Cloud Console
   - **Calendar ID**: ``primary`` (or specific calendar ID)
5. **Authorize the integration**:
   - Click "Authorize Google Meet"
   - Sign in with Google account (``movalagroingenieria@gmail.com``)
   - Grant necessary permissions
   - Verify that "✓ Google Meet integration is authorized" appears
6. **Test the connection**:
   - Click "Test Connection"
   - Verify success message appears

Configure appointment types
~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Go to Calendar → Configuration → Booking Types**
2. **For each appointment type you want to use Google Meet**:

   - Open the appointment type form
   - In the "Video Conference Settings" section:

     - Enable "Use Google Meet"

   - In the "Google Meet Settings" tab:

     - Customize description template if needed



Usage
=====

Automatic Operation
~~~~~~~~~~~~~~~~~~~

Once configured, the system works automatically:

1. **Client books online appointment** → System automatically generates Google Meet link
2. **Event created in Google Calendar** → With the ``movalagroingenieria@gmail.com`` account
3. **Client receives confirmation** → With Google Meet link included

Manual Management
~~~~~~~~~~~~~~~~~

* **View generated links**: In the calendar event form
* **Regenerate link**: "Regenerate Google Meet" button in events
* **Check status**: Visual indicator in list and kanban views


Integration Flow
================

1. **Appointment booking**::

    Client completes web form
    → Zehntech creates calendar.event
    → Our module intercepts creation
    → Google Meet generated if enabled
    → meeting_url updated with Google Meet link

2. **Google Meet generation**::

    Create event in Google Calendar
    → Configure conferenceData for Meet
    → Get generated Meet link
    → Store in google_meet_url and meeting_url fields


Extension Points
================

calendar.booking.type Model
~~~~~~~~~~~~~~~~~~~~~~~~~~~

* ``use_google_meet``: Enable/disable Google Meet per type

calendar.event Model
~~~~~~~~~~~~~~~~~~~~

* ``google_meet_url``: Generated Google Meet link
* ``google_event_id``: Google Calendar event ID
* ``google_meet_generated``: Generation status

Controller
~~~~~~~~~~

* Interception at ``/website/calendar/book``
* OAuth callback at ``/google_meet/oauth/callback``


Troubleshooting
===============

Error: "Google APIs not installed"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

Error: "Connection test failed"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Verify Google Cloud Console credentials
* Confirm APIs are enabled
* Verify redirect URI is configured

Error: "Authorization failed"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Verify Google account has permissions
* Confirm Client ID and Client Secret
* Verify domain is authorized in Google Cloud Console

Google Meet not generated automatically
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Verify "Use Google Meet" is enabled in appointment type
* Confirm integration is authorized
* Check Odoo logs for specific errors


Compatibility
=============

* **Odoo**: 16.0 Community Edition
* **Zehntech Appointment Booking**: v16.0.1.1.0+
* **Python**: 3.8+
* **Google APIs**: Current version


Credits
=======

* Moval Agroingeniería S.L.

Authors
~~~~~~~

* Moval Agroingeniería S.L.

Contributors
~~~~~~~~~~~~

* Guillermo Amante <gamante@moval.es>
* Juan José Bautista <jjbautista@moval.es>
* Samuel Fernández <sfernandez@moval.es>
* Pablo García <pgarcia@moval.es>
* Alberto Hernández <ahernandez@moval.es>
* Eduardo Iniesta <einiesta@moval.es>
* Jesús Martínez <jmartinez@moval.es>
* José Javier Méndez <jjmendez@moval.es>
* Miguel Mora <mmora@moval.es>
* Miguel Ángel Rodríguez <marodriguez@moval.es>
* Juanu Sandoval <jsandoval@moval.es>
* Salvador Sánchez <ssanchez@moval.es>
* Jorge Vera <jvera@moval.es>

Maintainers
~~~~~~~~~~~

This module is maintained by Moval Agroingeniería.

.. image:: https://services.moval.es/static/images/logo_moval_small.png
   :alt: Moval Agroingeniería
   :target: http://moval.es