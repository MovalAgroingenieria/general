.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

========================================
Account Banking Debit External Collector
========================================

Description
===========

This module generate a payment file for 'External Collector'. The module
creates two fields in the invoice:

* In collection (Boolean)
* External Collector Ref. (Text)

These fields are completed when the payment file is generated. What allows to
track and find the invoices sent to the external collector.


Notes
=====
After installation, it is mandatory to create a payment mode called
'ext_collector' associated with the payment method 'External collector'.

Credits
=======

* Moval Agroingeniería S.L.

Contributors
------------

* Javier Abril <jabril@moval.es>
* Ana Gómez <anaj.gomez@carm.es>
* Alberto Hernández <ahernandez@moval.es>
* Eduardo Iniesta <einiesta@moval.es>
* Miguel Mora <mmora@moval.es>
* Juanu Sandoval <jsandoval@moval.es>
* Jorge Vera <jvera@moval.es>

Maintainer
----------

.. image:: https://raw.githubusercontent.com/MovalAgroingenieria/public-assets/master/logos/logo_moval_small.png
   :target: http://moval.es
   :alt: Moval Agroingeniería

This module is maintained by Moval Agroingeniería.
