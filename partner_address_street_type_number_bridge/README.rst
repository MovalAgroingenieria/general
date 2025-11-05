.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

Street Type Street Number Bridge
==================================

Overview
========
This bridge module allows **Partner Address Street Type** and **Partner Address Street Number**
to coexist cleanly in Odoo 18. It merges both modules’ context definitions on the
``child_ids`` field of ``res.partner`` so that address creation inherits both
``street_type_id`` and ``street_num`` values from the parent partner.

Without this bridge, installing both modules would cause one of them to
overwrite the other’s context in the partner form view.

Features
========
- Merges the ``child_ids`` context of both modules.
- Ensures that child address creation receives:
  - ``default_street_type_id`` (from *Partner Address Street Type*).
  - ``default_street_num`` (from *Partner Address Street Number*).
- Compatible with Odoo **v18.0+**.
- Does **not** alter business logic or models — it only unifies view definitions.
- Loads with high priority so it safely overrides the partial contexts from
  the individual modules.

Dependencies
============
- ``partner_address_street_type``
- ``partner_address_street_number``

Installation
============
1. Add this module to your addons path.
2. Update the app list.
3. Install *Street Type  Street Number Bridge*.

Example (CLI)
-------------
::
   odoo-bin -d <db> -i partner_address_street_type_number_bridge

Technical Details
=================
The module defines a single inherited view of ``base.view_partner_form`` with
a merged ``context`` on the ``child_ids`` field::

   <field name="child_ids" position="attributes">
       <attribute name="context">
           {
               'default_parent_id': id,
               'default_street': street,
               'default_street2': street2,
               'default_city': city,
               'default_state_id': state_id,
               'default_zip': zip,
               'default_country_id': country_id,
               'default_lang': lang,
               'default_user_id': user_id,
               'default_type': 'other',
               'default_street_num': street_num,
               'default_street_type_id': street_type_id
           }
       </attribute>
   </field>

This ensures that when creating child addresses from a partner record, both
``street_num`` and ``street_type_id`` are pre-filled from the parent.

Usage
=====
- Open any partner record.
- Under the **Contacts & Addresses** tab, create a new address.
- Both **Street Type** and **Street Number** will automatically default from the parent partner.

Compatibility
=============
- Tested on **Odoo 18.0 (OCB compatible)**.
- No functional changes to data models; only view integration.

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
