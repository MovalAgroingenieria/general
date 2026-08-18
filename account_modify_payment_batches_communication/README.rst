.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

============================================
Account Modify Payment Batches Communication
============================================

This module enables integration with a complementary application for managing
the modification of payment batches communication.

Description
===========

Modification of payment batches communication through complementary application.

Registers itself as ``modificar-comunicacion-remesas`` in ``moval.external.app`` (from
``moval_external_apps_auth``) on install, and provides the launcher model
``account.modify.payment.batches.communication`` (built on top of
``moval_external_apps_iframe``'s abstract screen).

Activating this app for a client
=================================

Installing this module registers the app but does **not** expose it to
this instance's regular employees yet — only Odoo administrators can
open it, to verify the URL/credentials are correct first.

To make it visible to this instance's employees:

1. **Settings > Autenticación > External Apps**, open "Modificar Comunicación Remesas".
2. Fill in **App URL**, **Keycloak Client ID/Secret** and **App Shared
   Secret** for the modificar-comunicacion-remesas Keycloak client. The OIDC client is
   application-specific; the service user configured in Auth Settings is
   instance-specific (``svc-<db_name>``).
3. Check **"Enabled for client"** and save.

See the ``moval_external_apps_auth`` README for the full explanation of
this gating mechanism.

Credits
=======

* Moval Agroingeniería S.L.

Contributors
------------

* Guillermo Amante <gamante@moval.es>
* Juan José Bautista <jjbautista@moval.es>
* Samuel Fernández <sfernandez@moval.es>
* Alberto Hernández <ahernandez@moval.es>
* Jose Mendez <jjmendez@moval.es>
* Miguel Mora <mmora@moval.es>
* Juanu Sandoval <jsandoval@moval.es>
* Jorge Vera <jvera@moval.es>

Maintainer
----------

.. image:: https://raw.githubusercontent.com/MovalAgroingenieria/public-assets/master/logos/logo_moval_small.png
   :target: http://moval.es
   :alt: Moval Agroingeniería

This module is maintained by Moval Agroingeniería.
