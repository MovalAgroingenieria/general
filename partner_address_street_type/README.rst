.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

===========================
Partner Address Street Type
===========================

This module adds a *street type* field to partner addresses. The street type can be displayed
before the street in forms, list views, and printable documents. The display mode
(**full name** [default], **abbreviation**, or **hidden**) is configurable.

- Menu path: **Contacts → Configuration → Street Type Management → Settings**
- Alternatively: **Settings → Contacts** section

Key features
============

* New model: **res.street.type** with *name*, *abbreviation*, *is_default*, *show_in_list*, and *active*.
* New field on partners: **street_type_id** and computed helper **street_type_shown**.
* Display mode configurable via **ir.config_parameter**:
  - ``long`` → show full name
  - ``short`` → show abbreviation
  - ``not_show`` → hide
* Address format (**printing**) integration: the street type can be injected in the country
  **address_format** so it appears in reports and documents.
* Clean list/form views to manage street types and partner addresses.

Configuration
=============

1. Go to **Contacts → Configuration → Street Type Management → Settings** and choose how the
   street type should be displayed (full name, abbreviation, or hidden).
2. Optionally adjust the **address format** for your company country. The module can
   prepend the street type to the **street** field. This only applies to the company country
   and can be changed again from the same settings screen.
3. Create/import your country-specific street types (names and abbreviations vary by country).

Printing behavior
=================

If enabled in settings, the module updates the target country’s ``address_format`` so the
street type is placed **before** the street. This affects how addresses are rendered in
reports and documents that rely on the standard address rendering.

Compatibility
=============

* **Odoo 18.0**
* The module is data-agnostic: it defines the model and UI. Country-specific street types
  should be provided by another module or imported by you.

Installation
============

1. Install dependencies: ``contacts`` and ``base_setup``.
2. Update your apps list and install **Partner Address Street Type**.
3. (Optional) Import your street types via CSV/XLSX.

Usage
=====

* Open a partner and select a **Street type** (e.g., “Av.” / “Avenida”).
* The computed helper **street_type_shown** adapts to the configuration (long/short/hidden).
* In list views where inline editing is enabled, you can quickly adjust street types.

Access rights
=============

* Includes standard access rules via ``ir.model.access.csv``.
* Street types are manageable by users with access to the Contacts configuration.

Known issues / Roadmap
======================

* The street type dataset is intentionally **not** provided here; load your own data per country.
* Consider creating a small “data” module per country with pre-filled types and abbreviations.

Bug tracker
===========

If you find a bug or want to propose an enhancement, please open an issue
in your project repository and include steps to reproduce and logs where possible.

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
* Juanu Sandoval <jsandoval@moval.es>
* Salvador Sánchez <ssanchez@moval.es>
* Jorge Vera <jvera@moval.es>

Maintainer
----------

.. image:: https://services.moval.es/static/images/logo_moval_small.png
   :target: http://moval.es
   :alt: Moval Agroingeniería

This module is maintained by **Moval Agroingeniería**.

License
=======

AGPL-3.0 or later (see the badge above).
