.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

============================================
Transform database in demo database (DANGER)
============================================

Description
===========

This module transforms the records from 'res.partner' and 'res.company' into
records for demos.

WARNING: the installation of this module will irreversibly modify the
database.

.. list-table:: Transformations
   :align: center
   :widths: 60 10 60
   :header-rows: 0

   * -
     -
     -
   * - Firstname Lastname Lastname2
     - -->
     - María Demo Lastname2
   * - Phone / Mobile / email
     - -->
     - Ours Phone / Mobile / email
   * - Bank accounts
     - -->
     - Fakes bank accounts
   * - Company name
     - -->
     - Compañía Demo
   * - VAT
     - -->
     - Fake VAT
   * - Users password
     - -->
     - The same password for every user
   * - Attachments
     - -->
     - All attachments are deleted
   * - Mail server and google agenda
     - -->
     - Blocked

Credits
=======

* Moval Agroingeniería S.L.

Contributors
------------

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

Maintainer
----------

.. image:: https://services.moval.es/static/images/logo_moval_small.png
   :target: http://moval.es
   :alt: Moval Agroingeniería

This module is maintained by Moval Agroingeniería.
