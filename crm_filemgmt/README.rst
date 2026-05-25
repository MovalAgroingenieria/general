.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

===============
File Management
===============

Manage files in a structured way and associate them with any record in Odoo.
Create categories, containers, tags, and relationships between files, and control who can see and act on them.

Key Features
============

* File master model with yearly code pattern (e.g. ``TST-2025/0001``).
* Stages (Draft/In Progress/Closed) with kanban support and closing rules.
* Categories, Locations, Containers, and Container Types.
* Partner links (primary/secondary) and file-to-file links with constraints.
* Tags with color index for quick visual cues.
* Comments and HTML templates (top/bottom) with Jinja rendering per file.
* QWeb base report for files.
* Configuration in *Settings* → *File Management* (company-scoped file prefix).
* Access checks to hide actions for non-authorized users.

Access Rights
=============

* **File User** (``crm_filemgmt.group_file_user``): Can access the app and manage files.
* **Portal/User without file rights**: Views and actions sensitive to permissions are hidden.
* **Administrators** (``base.group_system``): Can configure the file prefix and global settings.

Installation
============

1. Make sure the technical dependencies are installed (OCB/Odoo 18).
2. Add the module to your addons path.
3. Update/Install the module:

   .. code-block:: bash

      odoo-bin -d <DB> -i crm_filemgmt

Configuration
=============

* Go to ``Settings --> Configuration --> File Management``.
* Set **File Prefix** (company dependent). The generated code format is ``<prefix>-<year>/<4-digit-number>``.

Usage
=====

* Open ``Files --> File Management``.
* Create a **File**, set **Subject**, **Stage**, **Category**, and (optionally) **Technician**.
* Link **Partners** (mark one as *Primary*) and related **Files** (no duplicates, no self link).
* Use **Tags** for quick filtering and color highlighting.
* Add **Top/Bottom comments** or **Templates** (Jinja) and print the **Base Report**.

Reporting
=========

A base QWeb report is provided:

* **Action**: ``crm_filemgmt.res_file_report_base``
* **Template**: ``crm_filemgmt.file_report_base_document``

Compatibility
=============

* Odoo/OCB **18**.
* Multi-company supported (file prefix is company dependent).
* Kanban stages folded/unfolded supported.

Testing
=======

Run unit tests (models, views, reports):

.. code-block:: bash

   odoo-bin -d <DB> -i crm_filemgmt --test-enable --stop-after-init

Known Constraints
=================

* Primary partner must be unique (exactly one when partner links exist).
* File-to-file links cannot reference the same file nor duplicate relationships.
* Closing stage transitions are restricted via onchange/UI guard.

Credits
=======

* Moval Agroingeniería S.L.
* The iconset has been generated using `IcoMoon <https://icomoon.io/>`_.
  Solid and duotone icons are available.

Contributors
------------

* Guillermo Amante <gamante@moval.es>
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

Maintainer
----------

.. image:: https://raw.githubusercontent.com/MovalAgroingenieria/public-assets/master/logos/logo_moval_small.png
   :target: http://moval.es
   :alt: Moval Agroingeniería

This module is maintained by Moval Agroingeniería.

License
=======

AGPL-3 (see the badge above).
