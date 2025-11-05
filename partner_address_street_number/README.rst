.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

Partner Address Street Number
=============================

Overview
========
This module adds a **street number** (`street_num`) field to partner addresses and integrates it into forms, lists, and address formatting.
By default, the number is displayed **after** the street in partner views. For printed documents, the **company country’s** address format is adjusted automatically; you can customize the position per country in *Contacts → Localization → Countries*.

If the *Partner Address Street Type* module is also installed, you can additionally manage formatting from:
*Contacts → Configuration → Street Type Management → Settings*.
That configuration only affects the **company’s country**.

Features
========
- New field `street_num` on **res.partner**.
- View extensions for:
  - Main partner form and address edit form (v18 compliant, using ``modifiers``).
  - Optional partner list (tree) column.
  - Embedded child address form under ``child_ids`` (with context propagation).
- Address formatting:
  - Hook injects ``%(street_num)s`` into the **company country** ``res.country.address_format``.
  - Safe, idempotent injection with per-country backup on uninstall.
- Context defaults:
  - ``default_street_num`` is propagated when creating child addresses from a partner.

Compatibility
=============
- **Odoo 18.0** (OCB compatible).
- Uses v17+/v18 patterns (``modifiers`` instead of deprecated ``attrs``).
- Hook signatures are forward/back compatible (accept ``env`` or ``cr, registry``).

Installation
============
1. Add the addon to your addons path.
2. Update the app list and install **Partner Address Street Number**.

   Example (CLI):
   ::
     odoo-bin -d <db> -i partner_address_street_number

Configuration
=============
- Country address format:
  - Go to *Contacts → Localization → Countries → (open your country)* and include
    ``%(street)s %(street_num)s`` (or any desired position).
  - The module’s post-init hook injects this token for the company country automatically.
- Optional list column:
  - In list (tree) views, the ``street_num`` column is marked ``optional="show"`` so users can toggle it.

Usage
=====
- Edit any partner or child address and fill **Street number** next to **Street**.
- Printed addresses (reports, labels, etc.) will include the number according to each country’s ``address_format``.

Uninstall
=========
- The uninstall hook restores the per-country address format backup (if available) or safely strips the token.

Testing
=======
- Run the test suite (recommended with workers=0):
  ::
     odoo-bin -d <db> -u partner_address_street_number --test-enable --workers=0 --stop-after-init

Internationalization
====================
- Export/update translations as usual:
  ::
     odoo-bin -d <db> --i18n-export=partner_address_street_number/i18n/es.po --language=es_ES --modules=partner_address_street_number

Known Limitations
=================
- If you have heavy customizations of partner views, you may need to adapt the inheritance targets.
- Ensure your reports use the standard address rendering or include ``%(street_num)s`` where appropriate.

Security / Access Rights
========================
- No special access rights are required beyond standard *Contacts* permissions.

License
=======
AGPL-3.0 or later (see badge/link above).

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
   :target: http://moval.es
   :alt: Moval Agroingeniería

This module is maintained by **Moval Agroingeniería**.
