.. |badge1| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

|badge1|

========================================
Account Payment Order: Payment Line Date
========================================

**Table of contents**

.. contents::
   :local:

Overview
========

This module adds a **requested payment date** to payment lines of a payment order
and exposes it in the *account.payment* list used inside the payment order form.

Features
========

* New field on payment lines to store the requested payment date.
* Form inheritance on **account.payment.order** to open the lines with a specific list view.
* List inheritance on **account.payment** to display the requested payment date right after the *name* column.

Usage
=====

1. Go to *Invoicing/Accounting → Vendors/Customers → Payment Orders*.
2. Open or create a payment order.
3. Add payment lines; the list view shows the **Requested Payment Date** column.
4. Set a date per line as needed.

Compatibility
=============

* Odoo/OCB **18.0**.

Installation
============

1. Install the module as usual from *Apps*.
2. Make sure the module **account_payment_order** (or your distribution’s equivalent) is installed and available, as this module inherits its views.

Known issues / Roadmap
======================

* None at the moment.
* Future: add domain/filters to ease planning by requested date.

Credits
=======

Authors
~~~~~~~

* Moval Agroingeniería S.L.

Contributors
~~~~~~~~~~~~

* Samuel Fernández Verdú <sfernandez@moval.es>
* Alberto Hernández <ahernandez@moval.es>
* Eduardo Iniesta <einiesta@moval.es>
* Jesús Martínez <jmartinez@moval.es>
* Miguel Mora <mmora@moval.es>
* Miguel Ángel Rodríguez <marodriguez@moval.es>
* Juanu Sandoval <jsandoval@moval.es>
* Salvador Sánchez <ssanchez@moval.es>
* Jorge Vera <jvera@moval.es>
* César Andrés <candres@moval.es>

Maintainers
~~~~~~~~~~~

This module is maintained by Moval Agroingeniería.

.. image:: https://raw.githubusercontent.com/MovalAgroingenieria/public-assets/master/logos/logo_moval_small.png
   :alt: Moval Agroingeniería
   :target: http://moval.es
