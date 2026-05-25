.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

===============================
Remote Control Engine: Hermisan
===============================

Hermisan SCADA/PLC REST API integration for pumping station monitoring.

Features
========

* Multi-endpoint connection: each physical Hermisan server (PLC) is an
  independent endpoint with its own credentials.
* Automatic catalog discovery: detects zones, pumping stations and pumps via
  ``BOMBEOCHECK`` and auto-creates devices/sensors.
* Historical readings import: queries ``BOMBEOSTATS`` by date ranges and stores
  pumping cycle data (water volume, power, flow, pressure, etc.).
* Automatic rate limiting (1 request/minute per endpoint).

Configuration
=============

1. Install the module.
2. In the **Hermisan** remote control, fill ``connection_params`` with the
   real endpoints::

     {
       "endpoints": {
         "bombeo_a": {
           "url": "https://xxxxx.hermisan.es",
           "username": "user",
           "password": "pass"
         }
       },
       "timezone": "Europe/Madrid"
     }

3. Run the **Catalog Sync** procedure to discover devices.
4. Run the **Import Readings** procedure to fetch historical data.

Technical Notes
===============

* ``BOMBEOSTATS`` response time can exceed 60 seconds on first query for a
  given period. Recommended timeout: 180s.
* Sending a request within 1 minute of the previous one returns ``false``.
* Fail2ban is active on servers: do not retry with wrong credentials.
* Zone names with double brackets (``[[EMBALSE B]]``) are hidden in
  Hermisan's UI; stripped automatically during parsing.

Credits
=======

 * Moval Agroingeniería S.L.

Contributors
------------
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
Maintainer
----------

.. image:: https://raw.githubusercontent.com/MovalAgroingenieria/public-assets/master/logos/logo_moval_small.png
   :target: http://moval.es
   :alt: Moval Agroingeniería

This module is maintained by Moval Agroingeniería.
