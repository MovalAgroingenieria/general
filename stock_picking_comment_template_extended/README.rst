.. |badge1| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

|badge1|

=========================
Picking Comments Extended
=========================

**Table of contents**

.. contents::
   :local:


Description
===========

This module changes how comment templates are added to stock picking reports.

- Comment templates (top/bottom) are **not** injected automatically into the report.
- Users must explicitly click the **Insert comments** button on the picking form.
- The action renders the selected templates (respecting their order and position)
  and writes the resulting HTML into two editable fields: **Top Comment** and **Bottom Comment**.
- Editing these fields **does not affect** the original templates.

Why this is useful
------------------

- Full control over when comments appear on each picking.
- Ability to fine-tune the generated text per document, without altering templates.


Compatibility
=============

- **Odoo:** 18.0
- **Depends on:** ``stock`` and the base comment template module
  (e.g. ``stock_picking_comment_template`` or your equivalent).


Usage
=====

1. Go to **Inventory → Operations → Transfers** and open a picking.
2. In the **Comments** tab, select the desired comment templates.
3. Click **Insert comments**.
4. Optionally edit **Top Comment** and/or **Bottom Comment** fields before printing.
5. Print the picking report (Delivery Slip / Picking Operations) to see the result.

Notes
-----

- The HTML in **Top Comment** and **Bottom Comment** is rendered in the report.
- The fields are read-only when the picking is **Done** or **Cancelled** (v18 uses JSON ``modifiers``).


Configuration
=============

No special configuration is required. Install the module and use the action from the picking form.


Uninstallation
==============

On uninstall, no data migration is performed. Existing values in the comment fields remain in the database but will no longer be injected by this module’s views/reports.


Credits
=======

Authors
-------

* Moval Agroingeniería S.L.

Contributors
~~~~~~~~~~~~

* Alberto Hernández <ahernandez@moval.es>
* Eduardo Iniesta <einiesta@moval.es>
* Jesús Martínez <jmartinez@moval.es>
* Miguel Mora <mmora@moval.es>
* Salvador Sánchez <ssanchez@moval.es>
* Juanu Sandoval <jsandoval@moval.es>
* Jorge Vera <jvera@moval.es>

Maintainers
~~~~~~~~~~~

This module is maintained by Moval Agroingeniería.

.. image:: https://services.moval.es/static/images/logo_moval_small.png
   :alt: Moval Agroingeniería
   :target: http://moval.es
