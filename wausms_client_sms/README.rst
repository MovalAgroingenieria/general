.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

=================
WauSMS client SMS
=================


Description
===========
Send SMS message to one or several partners using WauSMS services and keep a
record of the SMS sent. You can also send SMS from invoices. You can also
create templates, partner or invoice, with jinja2 variables for bulk or
individual sending.

Configuration
=============
In Configuration/Technical/WauSMS/Configuration set the WauSMS parameters:

* URL (usually https://dashboard.wausms.com/api/rest/message)
* API username
* API password

The default sender is also mandatory.

The mobile test phone is only necessary for sending SMS test.

The default subject is optional.

Set permission
--------------

By default everybody can see the SMS sent to particular partner, but in order to be able
to send SMS message the checkbox in Technical Settings/Can send SMS has to be marked for
each user that needs to send SMS messages. Admin user is added to this group by default.

Credits
=======

* Moval Agroingeniería S.L.

Contributors
------------

* Alberto Hernández <ahernandez@moval.es>
* Eduardo Iniesta <einiesta@moval.es>
* Miguel Mora <mmora@moval.es>
* Juanu Sandoval <jsandoval@moval.es>
* Salvador Sánchez <ssanchez@moval.es>
* Jorge Vera <jvera@moval.es>

Maintainer
----------

.. image:: https://services.moval.es/static/images/logo_moval_small.png
   :target: http://moval.es
   :alt: Moval Agroingeniería

This module is maintained by Moval Agroingeniería.
