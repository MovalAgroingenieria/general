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
