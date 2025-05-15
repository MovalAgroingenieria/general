.. |badge1| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

|badge1|

=============================
Account Invoice Fixed Concept
=============================

**Table of contents**

.. contents::
   :local:

Description
===========

The **Account Invoice Fixed Concept** module introduces a new invoice report where the invoicelines are replaced by a fixed concept defined by the user.
This is useful when a simplified or generic invoice format is required, where detailed product or service lines are not necessary.

Key Features:
* Adds a new invoice report with a fixed concept.
* The fixed concept is fully configurable by the user.
* Allows switching between the standard invoice report and the fixed concept invoice report.
* Simplifies the invoice layout by displaying a single, fixed concept.

Configuration
=============

1. Go to **Account > Configuration > Invoicing > Fixed concepts**.
2. Create a **Fixed Concept** and choose is the default concept.

Usage
=====

1. When generating an invoice, the user can select in the **Other information** tab the fixed concept configured previously.
2. The report **Invoice without details** shows the general information of the invoice but omits the detailed product lines, replacing them with the fixed concept, the total amount remains the same.

Screenshots
===========

.. image:: account_invoice_fixed_concept/static/img/screenshot_01.png
   :alt: Configuration and usage for the fixed invoice concept

Credits
=======

Authors
-------

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

This module is maintained by Moval Agroingeniería.

.. image:: https://services.moval.es/static/images/logo_moval_small.png
   :alt: Moval Agroingeniería
   :target: https://moval.es
