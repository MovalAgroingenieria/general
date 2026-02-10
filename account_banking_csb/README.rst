.. |badge_license| image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

|badge_license|

===================
Account Banking CSB
===================

**Table of contents**

.. contents::
   :local:

Description
===========

This module generates **CSB fixed-width payment files** for Spain from payment
orders in Odoo 18. It adds a custom payment method code
``csb_direct_debit_payments`` and extends the payment order flow to build the
CSB blocks (headers, beneficiary records, totals) with correct field widths and
padding.

Key points:

- Works with **Odoo 18** and OCA **bank-payment** stack.
- Uses company bank account on the payment order to compose the CSB header.
- Handles beneficiary name/address, ZIP, city, state, country, amounts, dates.
- Robust text conversion (accents → ASCII) and fixed-width formatting helpers.
- Designed to be **strict** about record lengths (100 chars + CRLF).

Compatibility
=============

- **Odoo**: 18.0
- **Depends**: OCA *bank-payment* (e.g. ``account_payment_order``, ``account_payment_mode``)
- **Payment method code**: ``csb_direct_debit_payments``

Installation
============

1. Install the OCA dependencies (bank-payment suite).
2. Add this add-on path to your Odoo configuration.
3. Update the app list and install **Account Banking CSB**.

Configuration
=============

Payment Method & Mode
---------------------

- Ensure the payment method **CSB Direct Debit** (``csb_direct_debit_payments``)
  is available (loaded from this module’s data).
- Create a **Payment Mode** and set *Payment Method* to ``csb_direct_debit_payments``, *Initiating Party Identifier* (or Issuer) to your company identifier (e.g. NIF), and *Bank Account Link* to a strategy your OCA branch validates. If you use **Fixed**, set a **fixed bank journal** pointing to a company bank account. If you use **Company**, make sure the company has a bank account.

Company Bank Account
--------------------

- On the company partner, create a **Bank Account**. Prefer a **20-digit CCC** for CSB lines that expect digits-only. IBANs are accepted elsewhere but some CSB fields require clean numeric data.

Usage
=====

1. Create a **Payment Order** with method ``csb_direct_debit_payments`` and the
   payment mode configured above.
2. Add **Payment Lines** (beneficiaries with VAT and addresses).
3. Click **Generate File** to get the CSB text file.

The generator strictly checks that each CSB record line is **exactly 100 chars**
(plus CRLF). Any mismatch raises an explicit error with the failing block name.

Notes for CI
------------

- Some OCA branches enforce additional constraints (e.g., *bank_account_link*).
  The tests create a **bank journal** and a **20-digit CCC** to satisfy them.

Known limitations
=================

- CSB layouts are strict. Customizations that alter string lengths or encodings
  may break validation.
- VAT and ZIP are treated as **text identifiers** (not numbers) and padded to
  fixed width.

Credits
=======

Authors
-------

* Moval Agroingeniería S.L.

Contributors
------------

* Alberto Hernández <ahernandez@moval.es>
* Eduardo Iniesta <einiesta@moval.es>
* Miguel Mora <mmora@moval.es>
* Salvador Sánchez <ssanchez@moval.es>
* Juanu Sandoval <jsandoval@moval.es>
* Jorge Vera <jvera@moval.es>
* César Andrés <candres@moval.es>

Maintainers
-----------

This module is maintained by Moval Agroingeniería.

.. image:: https://services.moval.es/static/images/logo_moval_small.png
   :alt: Moval Agroingeniería
   :target: http://moval.es
