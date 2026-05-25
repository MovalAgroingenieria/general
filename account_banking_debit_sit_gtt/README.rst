.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

=============================
Account Banking Debit SIT GTT
=============================


Description
===========

This module generate a normalized payment file for organizations that use the
Tax Information System `SIT <https://www.gtt.es/sistema-informacion-tributario>`_
created by the company `GTT <https://www.gtt.es/empresa/>`.


Notes
=====

After installation, it is mandatory:

* create a payment mode called **SIT GTT** associated with the payment method **SIT-GTT**.

* configure the entity code in /Accounting/Configuration/Configuration section "Tax management system (SIT GTT)".

It is also advisable not to use the option "Group transactions in payment orders", in the configuration options
of the **SIT GTT** payment mode (each transaction will be a bank payment line).


Credits
=======

* Moval Agroingeniería S.L.


Contributors
------------

* Guillermo Amante <gamante@moval.es>
* Ana Bernal <abernal@sit_gtt.es>
* Samuel Fernández <sfernandez@moval.es>
* Pablo García <pgarcia@moval.es>
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

.. image:: https://raw.githubusercontent.com/MovalAgroingenieria/public-assets/master/logos/logo_moval_small.png
   :target: http://moval.es
   :alt: Moval Agroingeniería

This module is maintained by Moval Agroingeniería.
