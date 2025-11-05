.. |badge1| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

|badge1|

================================
Account Payment Partner Extended
================================

**Table of contents**

.. contents::
   :local:


Overview
========
This addon extends the partner payment features provided by the base
*account_payment_partner* suite. It introduces a computed, stored helper field
on partners to ease searching, filtering, and reporting by the configured
customer payment mode.

Key Features
============
* Adds a related, stored field (``computed_customer_payment_mode_id``) that mirrors
  the partner’s ``customer_payment_mode_id`` for fast searches and domain filters.
* Fully compatible with Odoo 18 (OCB/CE).
* No changes to standard business flows; purely additive.

Usage
=====
1. Open **Contacts** and pick any partner.
2. Set **Customer Payment Mode** as usual.
3. Use the stored helper field **Computed Customer Payment Mode** in search
   domains, filters, or record rules for efficient lookups.

Configuration
=============
No configuration is required. The module works out of the box after installation.

Compatibility
=============
* Odoo 18.0 (Community/OCB)

Known Limitations
=================
* This module does not alter payment generation; it only exposes a stored mirror
  of the configured mode to improve filtering and performance.

Bug Tracker
===========
If you spot a problem or have a feature request, please open an issue in your
project tracker or contact the maintainers listed below.

Credits
=======

Authors
-------
* Moval Agroingeniería S.L.

Contributors
------------
* Alberto Hernández <ahernandez@moval.es>
* Eduardo Iniesta <einiesta@moval.es>
* Jesús Martínez <jmartinez@moval.es>
* Miguel Mora <mmora@moval.es>
* Salvador Sánchez <ssanchez@moval.es>
* Juanu Sandoval <jsandoval@moval.es>
* Jorge Vera <jvera@moval.es>

Maintainers
-----------
This module is maintained by **Moval Agroingeniería**.

.. image:: https://services.moval.es/static/images/logo_moval_small.png
   :alt: Moval Agroingeniería
   :target: http://moval.es

License
=======
AGPL-3.0 or later (see the badge above).
