.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

==============
NRS client SMS
==============

Description
===========
Send normal or certified SMS messages with legal validity by verified sender by
Google (*) to one or several partners using 360NRS services and keep a record of
the SMS sent and their certificates.

You can also send SMS from invoices. You can also create templates, partner or
invoice, with jinja2 variables for bulk or individual sending.

.. note::
   Certified SMS have a higher cost, € 0.20/SMS.
   See `<https://en.360nrs.com/channels/sms/certificates/>`_

Configuration
=============
In Configuration/NRS SMS/Configuration set the 360NRS parameters:

* URL (usually https://dashboard.360nrs.com/api/rest/sms)
* API username
* API password

The default sender is also mandatory.

(*) The verified sender by Google has to be configured in 360NRS website,
see `<https://www.360nrs.com/advantages/google-verified/>`_.

The mobile test phone is only necessary for sending SMS test.

The default subject is optional.

Set permission
--------------

By default everybody can see the SMS sent to particular partner, but in order
to be able to send SMS message the checkbox in Technical Settings/Can send SMS
has to be marked for each user that needs to send SMS messages. Admin user is
added to this group by default.

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


Financial contributors
----------------------

* Comunidad General de Regantes Sector A) Zona II de las Vegas Alta y Media del Segura
* Comunidad de Regantes de Tavalera la Real
* Comunidad de Regantes de las Aguas Reguladas por el Embalse del Argos
* Comunidad de Regantes Trasvase Tajo Segura de Librilla
* Comunidad de Regantes de Alhama de Murcia

Maintainer
----------

.. image:: https://raw.githubusercontent.com/MovalAgroingenieria/public-assets/master/logos/logo_moval_small.png
   :target: http://moval.es
   :alt: Moval Agroingeniería

This module is maintained by Moval Agroingeniería.
