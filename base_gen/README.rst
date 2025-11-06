.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: https://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

===================
Base - General Tools
===================

Overview
========

General-purpose utilities for Odoo 18 modules:

* **Master data helpers** (code + description patterns, display names).
* **Common formatting** (locale-aware numbers/dates, accent stripping).
* **Sequence alignment** (predict/consume without desync).
* **Small validation hooks** and base mixins.

This module is intended as a lightweight foundation you can inherit in other apps.

Compatibility
=============

* **Odoo/OCB**: 18.0
* Python: 3.10+

Key Features
============

* `simple.model` abstract base for code/description entities.
* Locale-aware helpers for float/date formatting.
* Safe text utilities (trim, casing, max-length clipping).
* Optional numeric vs alphanumeric code modes.
* Clean `name_get` / `name_search` behavior.
* Predictive sequence usage (no-gap alignment).

Installation
============

Standard module install from Apps. No extra configuration required.
(Optional) If you want automatic alphanumeric proposals, set an
``ir.config_parameter`` key with an ``ir.sequence`` ID and point your
model to it (see “Sequences” below).

Configuration
=============

Sequences
---------

If you want to use an Odoo sequence for alphanumeric codes:

1. Create an **ir.sequence** (e.g. prefix, padding).
2. Store its ID in **Settings → Technical → Parameters → System Parameters**,
   under a key such as ``my.module.sequence_id``.
3. In your subclass of ``simple.model``, set:

   * ``_sequence_for_codes = "my.module.sequence_id"``

Numeric vs Alphanumeric Mode
----------------------------

* Set ``_set_num_code = True`` in your subclass to use numeric codes (auto-increment).
* Leave it ``False`` to use alphanumeric codes (with optional lowercase/uppercase).

Usage
=====

Inherit the abstract model and add your own fields:

.. code-block:: python

   from odoo import models, fields

   class MyThing(models.Model):
       _name = "my.thing"
       _inherit = "simple.model"

       # Optional tuning
       _set_num_code = False
       _size_name = 30
       _size_description = 75
       _sequence_for_codes = "my.thing.sequence_id"

       extra_field = fields.Char("Extra")

Testing
=======

This module includes unit tests for helpers and the base model. To run:

.. code-block:: bash

   odoo --test-enable -i base_gen --stop-after-init
   # or with OCB:
   odoo-bin --test-enable -i base_gen --stop-after-init

Credits
=======

* Moval Agroingeniería S.L.

Contributors
------------

* Alberto Hernández <ahernandez@moval.es>
* Eduardo Iniesta <einiesta@moval.es>
* Miguel Mora <mmora@moval.es>
* Juanu Sandoval <jsandoval@moval.es>
* Salvador Sánchez <ssanchez@moval.es>
* Jorge Vera <jvera@moval.es>

Maintainer
----------

.. image:: https://services.moval.es/static/images/logo_moval_small.png
   :target: https://moval.es
   :alt: Moval Agroingeniería

This module is maintained by **Moval Agroingeniería**.
