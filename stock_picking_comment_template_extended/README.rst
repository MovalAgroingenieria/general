.. |badge1| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl-3.0-standalone.html
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

This module extends the behavior of comment templates on stock picking reports.

By default, comment templates are injected automatically by the base module.
This extension changes that workflow to give users explicit control.

Key changes introduced by this module:

- Comment templates (top and bottom) are **not** injected automatically.
- Users must explicitly click the **Insert comments** button on the picking form.
- The action renders the selected templates (respecting order and position)
  and stores the resulting HTML in two editable fields:
  **Top Comment** and **Bottom Comment**.
- Editing these fields **does not affect** the original templates.


Why this is useful
------------------

- Full control over **when** comments are applied to a picking.
- Ability to fine-tune the generated text per document.
- Templates remain reusable and unchanged.


Compatibility
=============

- **Odoo:** 18.0
- **Depends on:**
  - ``stock``
  - ``stock_picking_comment_template`` (or an equivalent base module providing comment templates)


Usage
=====

1. Go to **Inventory → Operations → Transfers** and open a picking.
2. Open the **Comments** tab.
3. Select the desired comment templates.
4. Click **Insert comments**.
5. Optionally edit **Top Comment** and/or **Bottom Comment**.
6. Print the picking report (Delivery Slip or Picking Operations).

The rendered comments will appear in the corresponding report sections.


Notes
-----

- The HTML stored in **Top Comment** and **Bottom Comment** is rendered directly
  in the report.
- These fields become read-only when the picking is **Done** or **Cancelled**
  (Odoo 18 uses JSON ``modifiers`` for this behavior).


Configuration
=============

No special configuration is required.

Install the module and use the **Insert comments** action from the picking form.


Uninstallation
==============

No data migration is performed on uninstall.

Existing values stored in the comment fields remain in the database but will no
longer be injected into reports by this module.


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
   :target: https://www.moval.es
