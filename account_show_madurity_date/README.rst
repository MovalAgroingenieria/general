.. |badge1| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

|badge1|

==========================
Account Show Maturity Date
==========================

**Table of contents**

.. contents::
   :local:

Description
===========
This module modifies the behavior of the core *account* module to show the
**maturity date** by default in journal items. It achieves this by ensuring
the `date_maturity` column is visible and by ignoring the `view_no_maturity`
context flag when present.

Key Features
============
* Forces the `date_maturity` field to be visible in the *Journal Items* list.
* Ignores the `view_no_maturity` context parameter so the column is not hidden by views.

Usage
=====
No configuration is required. Once installed, open an invoice/bill
(*Accounting → Customers/Vendors → Invoices/Bills*) and go to the *Journal Items*
tab; the **Maturity Date** column will be visible by default.

Compatibility
=============
* Odoo 18.0

Credits
=======

Authors
~~~~~~~
* Moval Agroingeniería S.L.

Contributors
~~~~~~~~~~~~
* Alberto Hernández <ahernandez@moval.es>
* Eduardo Iniesta <einiesta@moval.es>
* Miguel Mora <mmora@moval.es>
* Salvador Sánchez <ssanchez@moval.es>
* Juanu Sandoval <jsandoval@moval.es>
* Jorge Vera <jvera@moval.es>
* César Andrés <candres@moval.es>

Maintainers
~~~~~~~~~~~
This module is maintained by Moval Agroingeniería.

.. image:: https://raw.githubusercontent.com/MovalAgroingenieria/public-assets/master/logos/logo_moval_small.png
   :alt: Moval Agroingeniería
   :target: http://moval.es
