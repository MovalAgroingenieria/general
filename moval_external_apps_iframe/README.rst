.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

==================================
Moval External Apps - Iframe Skeleton
==================================

Reusable skeleton for embedding external applications inside Odoo through an
authenticated full-screen iframe.

Description
===========

This module provides the abstract model ``moval.external.app.screen.abstract``,
which concentrates the shared behaviour for embedding an external application:

* Computes the ``app_frame`` HTML iframe via ``moval.auth.mixin._build_iframe``.
* ``action_open_iframe``: opens the app inside Odoo as an inline full-screen form.
* ``action_open_new_tab``: opens the app in a new browser tab with a single-use
  ticket.

Each application module defines a small concrete ``TransientModel`` that inherits
from this abstract model, sets its ``APP_SLUG`` and implements
``_get_form_view_xmlid`` to point at its own full-screen form view. The
application slug and its credentials are registered centrally in
``moval.external.app`` (from ``moval_external_apps_auth``).

Client access gating
=====================

Whether an instance's own employees can actually see and open the app is
**not** decided here. It depends on the "Enabled for client" checkbox on
the app's ``moval.external.app`` record — see the
``moval_external_apps_auth`` README for how to activate an app for a
given Odoo instance's users. Until it is enabled, only Odoo
administrators can open the screens provided by this module.

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
