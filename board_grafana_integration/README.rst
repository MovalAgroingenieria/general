.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

=========================
Board Grafana integration
=========================

Integration with Grafana for Odoo board module. This module enhance Odoo Board
module with Grafana.

Description
===========

This module allows you to connect to an Organization on a Grafana server
through proxy authentication for a user attached to that organization. In
addition, that organization must have a data source configured to connect to
the PostgreSQL database of your Odoo instance.

After the configuration you will be able to transparently connect to this
server and use the features of Grafana to extract metrics, analyze data or
create dashboards and panels.

Grafana API Key
---------------

The dashboards stored in Odoo are sent to Grafana with the token of a
Grafana service account with the Editor role (Grafana 13 no longer supports
the old API keys). The token is stored in the system parameter
``board_grafana_integration.api_key``, which is only readable by
administrators:

#. In Grafana, create a service account with the Editor role and generate a
   token for it.
#. In *Dashboards > Grafana > Settings*, the *Grafana API Key* line shows
   whether it is set. Press *Edit* to open the system parameter and paste
   the token into its *Value*.

It can also be edited in *Settings > Technical > Parameters > System
Parameters*. If it is created by hand, keep the group *Administration /
Settings* in it; applying the Grafana settings restores that group.

Automatic login (JWT)
---------------------

Odoo users are signed in to Grafana as a single Grafana user with the Viewer
role (e.g. ``odooreader``), so anonymous access is not needed. Odoo signs a
JWT (RS256) and Grafana checks it with the public key of Odoo:

#. Create the Grafana user (e.g. ``odooreader``) with the Viewer role in the
   organization and make that organization its default one.
#. In *Dashboards > Grafana > Settings*, set *Grafana user* and apply. An
   RSA key pair is generated; the private key is only readable by
   administrators and never reaches the browser.
#. Configure grafana.ini with the *JWT public key* shown in the settings,
   disable the anonymous access and allow embedding::

    [auth.anonymous]
    enabled = false

    [security]
    allow_embedding = true

    [auth.jwt]
    enabled = true
    header_name = X-JWT-Assertion
    username_claim = sub
    url_login = true
    auto_sign_up = false
    skip_org_role_sync = true
    key_value = <JWT public key>
    expect_claims = {"iss": "odoo", "sub": "odooreader"}

#. Restart Grafana.

Grafana pages are always opened through ``/board_grafana/auth?path=<path>``
(also full Grafana URLs are accepted). This route is only available to users
with access to the module (never portal users): it creates a new token valid
for 12 hours and redirects to Grafana with it. Other modules should use
``env['board.grafana'].get_grafana_auth_url(path)`` (or
``create_grafana_frame``) instead of the Grafana URL, which no longer works
without a session.

Modules that show Grafana to portal users can not use that route. They have
to add their own one and build the path on the server, from the session of
the portal user, so that its parameters can not be chosen by the browser,
and then sign it with ``_get_grafana_signed_url(path)``. This is what
``base_wua_portal_sensorreading_grafana`` does.

* ``expect_claims`` only accepts tokens for the configured user: even with
  the private key, no other Grafana user (e.g. ``admin``) can be impersonated.
* When the token expires, Grafana asks to log in: reload the panel.
* *Regenerate key* invalidates the current key: update grafana.ini again.
* *Dashboards > Grafana > Grafana server* opens Grafana in a new tab, also
  signed in automatically. Grafana users that edit dashboards have to open
  the Grafana login page (``<Grafana URL>/login``) themselves.
* A Viewer can still send queries to the data sources through the Grafana
  API, so keep the data source user read-only and restricted to the tables
  the dashboards need. This also applies to the portal users that reach
  Grafana through ``base_wua_portal_sensorreading_grafana``.

Side panel
----------

The module adds a Grafana icon to the top bar that opens Grafana in a side
panel on the right, available from any application. It shows the welcome
dashboard, or the dashboard list if none is set.

* The icon is disabled by default. Enable *Show navbar button* in
  *Dashboards > Grafana > Settings* to show it.
* The icon is only shown to users with access to the module (internal users),
  never to portal users.
* Grafana is loaded the first time the panel is opened and is kept while
  navigating between applications. Closing the panel only hides it.
* The panel can be resized by dragging its left edge. The width is saved in
  the browser.
* *Open in a new tab* opens the page being displayed in the panel.
* On wide screens (1400 px or more) the panel takes its space from the
  content. On smaller screens it floats over the content, and on phones it
  covers the whole screen.
* It can be open at the same time as the Open WebUI side panel
  (``openwebui_odoo_integration``); both panels are then shown side by side.

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

.. image:: https://raw.githubusercontent.com/MovalAgroingenieria/public-assets/master/logos/logo_moval_small.png
   :target: http://moval.es
   :alt: Moval Agroingeniería

This module is maintained by Moval Agroingeniería.
