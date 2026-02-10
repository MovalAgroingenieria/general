.. |badge1| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

|badge1|

=========================
Display Decimal Precision
=========================

**Table of contents**

.. contents::
   :local:

Description
===========

This module allows separating **calculation precision** from
**display precision** for decimal (float) fields in Odoo.

While Odoo internally computes values using a fixed precision,
the number of decimals shown to the user is often required to be different
(e.g. show 2 decimals while computing with 6).

This module introduces:

* A configurable **display precision layer** based on logical categories (e.g. *Product Price*, *Unit of Measure*).
* Global configuration through **Settings** (`res.config.settings`), stored in system parameters.
* Automatic application of display precision to field metadata sent to the UI and to QWeb reports.

The stored value is **never altered**: only the way decimals are *displayed*
is affected.

.. note::

   Currency rounding and monetary precision are **not modified** by this
   module and remain governed by standard Odoo currency settings.

How it works
============

* Display precisions are defined per logical *application name* (e.g. ``Product Price``).
* Values are stored in ``ir.config_parameter`` and can be edited from *General Settings*.
* Float fields declared with ``digits="Application Name"`` automatically receive the configured display precision.
* A lightweight override ensures consistent behavior across views, field descriptions, and QWeb rendering.

Usage
=====

To configure display precision:

1. Go to **Settings → General Settings**.
2. Locate the **Decimal display precision** section.
3. Set the number of decimals to display for each category
   (e.g. *Product Price*, *Product Quantity*).
4. Save the settings.

All fields using the corresponding precision category will immediately
reflect the new display precision throughout the system.

Credits
=======

Authors
~~~~~~~
* Moval Agroingeniería S.L.

Contributors
~~~~~~~~~~~~
* Alberto Hernández <ahernandez@moval.es>
* Eduardo Iniesta <einiesta@moval.es>
* Jesús Martínez <jmartinez@moval.es>
* Miguel Mora <mmora@moval.es>
* Juanu Sandoval <jsandoval@moval.es>
* Salvador Sánchez <ssanchez@moval.es>
* Jorge Vera <jvera@moval.es>
* César Andrés <candres@moval.es>

Maintainer
~~~~~~~~~~
This module is maintained by Moval Agroingeniería.

.. image:: https://services.moval.es/static/images/logo_moval_small.png
   :alt: Moval Agroingeniería
   :target: https://moval.es
