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

This module allows you to distinguish between **computation digits** and
**display digits** for decimal precision in numeric fields.

In Odoo 18, the legacy *decimal.precision* model has been removed.
This module reproduces its functionality by storing display-digit
preferences in system parameters and exposing them in *Settings*.

> Note that currencies are managed separately through their own rounding
> and decimal-place configuration.

Usage
=====

To edit a display precision:

1. Go to **Settings → General Settings → Display Precision** section.
2. Adjust the number of decimals you want to display for each category,
   such as *Product Price* or *Unit of Measure*.
3. Save the settings.
4. The configured values will automatically apply to fields that use
   those display precisions across the system.

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

Maintainer
~~~~~~~~~~
This module is maintained by Moval Agroingeniería.

.. image:: https://services.moval.es/static/images/logo_moval_small.png
   :alt: Moval Agroingeniería
   :target: https://moval.es
