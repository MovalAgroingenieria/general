.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

=======================
RemoteControl: ICC PRO
=======================

This module provides integration with ICC PRO remote control system via REST API.

ICC PRO is a water meter monitoring system that provides access to device data
and readings through an OAuth2-authenticated REST API.

Configuration
=============

1. Install this module
2. Go to Remote Controls menu
3. Configure the ICC PRO remote control with your credentials:
   - Base URL: http://your-server:81
   - Connection Params (JSON):
     {
       "username": "YOUR_USERNAME",
       "password": "YOUR_PASSWORD",
       "client_id": "YOUR_CLIENT_ID",
       "client_secret": "YOUR_CLIENT_SECRET"
     }

Usage
=====

The module provides the following procedures:

- **ICC PRO: Get Token** - Authenticates and obtains access token
- **ICC PRO: Daily Sync** - Synchronizes device readings

Credits
=======

* Moval Agroingeniería

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
