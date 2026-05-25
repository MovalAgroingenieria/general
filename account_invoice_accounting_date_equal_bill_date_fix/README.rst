.. |badge1| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

|badge1|


=======================================================
Account Invoice Accounting Date Equal Bill Date Fix
=======================================================

**Table of contents**

.. contents::
   :local:


Description
===========

Extends ``account_invoice_accounting_date_equal_bill_date`` to fix a crash
when duplicating vendor invoices.

The original module sets ``date = invoice_date`` unconditionally for vendor
invoices. Since ``invoice_date`` has ``copy=False``, it is empty in a
duplicated record, causing a ``NOT NULL`` constraint violation on
``account_move.date``.

This fix splits supplier moves into two groups before computing the date:

- **With** ``invoice_date``: keeps the original behaviour (``date = invoice_date``).
- **Without** ``invoice_date`` (e.g. during duplication): delegates to Odoo
  standard logic, which defaults to today's date.

Credits
=======

Authors
~~~~~~~

* Moval Agroingeniería S.L.

Contributors
~~~~~~~~~~~~

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

Maintainers
~~~~~~~~~~~

This module is maintained by Moval Agroingeniería.

.. image:: https://raw.githubusercontent.com/MovalAgroingenieria/public-assets/master/logos/logo_moval_small.png
   :alt: Moval Agroingeniería
   :target: http://moval.es
