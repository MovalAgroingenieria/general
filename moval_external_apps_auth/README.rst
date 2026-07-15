.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

===================================
Moval External Apps Authentication
===================================

Shared authentication framework for embedding external Moval applications
inside Odoo via an authenticated iframe, without ever exposing a per-user
Keycloak login to the browser.

Description
===========

This module owns the mechanism shared by every embedded external app:

* ``moval.service.ticket``: opaque, single-use ticket store (TTL 30s).
* ``moval.external.app``: per-app registry (URL, Keycloak client, shared
  secret, and client-access gating — see below).
* ``moval.auth.config``: instance-wide config (Keycloak token URL, service
  account username/password and optional externally reachable PostgreSQL
  endpoint).
* ``moval.auth.mixin``: shared methods (``_get_service_token``,
  ``_issue_ticket``, ``_build_iframe``, ``_get_app_url_with_ticket``) used
  by every app-specific module.
* ``/moval/redeem-ticket``: HTTP controller (``auth=none``) where the
  external app redeems a ticket server-to-server and receives back the
  Keycloak JWT. The JWT never reaches the browser.

App-specific modules (``wua_hydric_balance_manager``, ``moval_test_app``,
etc.) only provide their app slug, form view, and business logic — they
depend on ``moval_external_apps_iframe`` for the shared iframe/open-in-tab
screen, which in turn depends on this module for authentication.

How it works
============

1. An Odoo user opens the app's menu.
2. Odoo authenticates against Keycloak with a **service account** (password
   grant, configured once in ``moval.auth.config``) and gets a short-lived
   JWT.
3. Odoo mints an opaque, single-use ticket bound to that JWT and the app's
   slug (``moval.service.ticket.issue``).
4. The app is embedded with ``?ticket=<opaque>`` in its URL.
5. The external app calls ``POST /moval/redeem-ticket`` (with its own
   ``app_shared_secret`` as bearer auth) to exchange the ticket for the
   JWT, then mints its own session token. The Keycloak JWT is never sent
   to the browser.

The endpoint is an Odoo 10 ``type="http"`` route. Clients must send the JSON
body with ``Content-Type: text/plain``; ``application/json`` is reserved by
Odoo for JSON-RPC dispatch.

Configuration
=============

Settings > Autenticación > Auth Settings
   Configure once per Odoo instance: Keycloak token URL and the service
account (``moval_service_username`` / ``moval_service_password``) used
to obtain JWTs on behalf of the logged-in Odoo user.

Optionally configure **External PostgreSQL Host/Port** only when that endpoint
is reachable from the external app runtime. Leaving it empty returns null
connection metadata; the module never assumes ``localhost`` is externally
reachable.

Settings > Autenticación > External Apps
   One record per external app installed on **this** Odoo instance
   (``moval.external.app``):

   * **App URL**: base URL of the external app.
   * **Keycloak Client ID / Secret**: this app's own OIDC client in
     Keycloak. Each app must use a *different* client, so a leaked
     ticket/session for one app cannot be replayed against another.
   * **App Shared Secret**: bearer secret the external app must send when
      calling ``/moval/redeem-ticket``. Must match the app's own Odoo shared
      secret environment setting.
   * **Enabled for client** — see below.

How to activate an app for this instance's users
=================================================

Installing an app-specific module (e.g. ``wua_hydric_balance_manager``)
does **not**, by itself, expose the app to this instance's regular
employees. On install, the app module registers itself in
``moval.external.app`` with **"Enabled for client" unchecked**, which
means:

* The launcher menu is only visible to Odoo administrators
  (``base.group_system``).
* Regular employees (``base.group_user``) have **no** read/write access
  to the launcher model — this is enforced at the ``ir.model.access``
  level, not just menu visibility.

This lets Moval install and configure an app (URL, Keycloak
credentials, shared secret) on a client's instance, and verify it works
(as an administrator) **before** the client's own users can see or use it.

To activate the app for this instance's users:

1. Go to **Settings > Autenticación > External Apps**.
2. Open the app's record.
3. Check **"Enabled for client"** and save.

This immediately grants ``base.group_user`` access to the launcher model
and adds it back to the launcher menu's visible groups — no module
upgrade or restart required. Unchecking it reverts both, instantly
hiding the app again for this instance's regular users while keeping it
available to administrators.

Each Odoo instance manages this independently: enabling the app for one
client has no effect on any other instance.

The standard ``active`` field archives or disables the app configuration. It
is deliberately separate from ``client_access_enabled`` so Moval
administrators can test an active app while it remains hidden from employees.

Credits
=======

* Moval Agroingeniería S.L.

Contributors
------------

* Guillermo Amante <gamante@moval.es>
* Juan José Bautista <jjbautista@moval.es>
* Samuel Fernández <sfernandez@moval.es>
* Alberto Hernández <ahernandez@moval.es>
* Jesús Martínez <jmartinez@moval.es>
* José Javier Méndez <jjmendez@moval.es>
* Miguel Mora <mmora@moval.es>
* Juanu Sandoval <jsandoval@moval.es>
* Salvador Sánchez <ssanchez@moval.es>
* Jorge Vera <jvera@moval.es>

Maintainer
----------

.. image:: https://raw.githubusercontent.com/MovalAgroingenieria/public-assets/master/logos/logo_moval_small.png
   :target: http://moval.es
   :alt: Moval Agroingeniería

This module is maintained by Moval Agroingeniería.
