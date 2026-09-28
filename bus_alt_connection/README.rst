.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

==================
Bus Alt Connection
==================

This module provides an alternative connection method for the Odoo bus system,
allowing it to listen for PostgreSQL notifications on a direct connection.

This module has been backported to Odoo 10.0 from the OCA/server-tools
bus_alt_connection module in 12.0.


Description
===========

This module is particularly useful in scenarios where the standard Odoo bus
connection may not be sufficient or when a direct PostgreSQL connection is
preferred for performance or architectural reasons. For example, when using
pgbouncer as a connection pooler, a direct connection can help ensure that
PostgreSQL notifications are received reliably.


Credits
=======

* Moval Agroingeniería S.L.

Contributors
------------

* Guillermo Amante <gamante@moval.es>
* Juan José Bautista <jjbautista@moval.es>
* Samuel Fernández <sfernandez@moval.es>
* Alberto Hernández <ahernandez@moval.es>
* Jose Mendez <jjmendez@moval.es>
* Miguel Mora <mmora@moval.es>
* Juanu Sandoval <jsandoval@moval.es>
* Jorge Vera <jvera@moval.es>

Maintainer
----------

.. image:: https://raw.githubusercontent.com/MovalAgroingenieria/public-assets/master/logos/logo_moval_small.png
   :target: http://moval.es
   :alt: Moval Agroingeniería

This module is maintained by Moval Agroingeniería.
