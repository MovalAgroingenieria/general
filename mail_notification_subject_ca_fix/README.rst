.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

================================
Mail Notification Subject CA Fix
================================

This module fixes a broken Catalan translation (``ca_ES``) in the default
Odoo Mail notification email template subject
(``mail.mail_template_data_notification_email_default``).

The issue originates in the core ``mail`` module Catalan ``ca.po`` file,
where the Python/Mako operators ``or`` and ``and`` inside the template
expression were incorrectly translated to ``o`` and ``i``, causing a
``TemplateSyntaxError`` when the subject was rendered.

The fix is applied in two complementary ways:

- **post_init_hook**: updates the ``ir_translation`` row in the database
  immediately at module installation or update.
- **i18n_extra/ca_ES.po**: provides the corrected translation, which is
  loaded *after* all standard ``i18n`` translations on every language
  reload, ensuring it always overrides the broken entry from the core module.

Credits
=======

* Moval Agroingeniería S.L.

Contributors
------------
* Guillermo Amante <gamante@moval.es>
* Samuel Fernández <sfernandez@moval.es>
* Pablo García <pgarcia@moval.es>
* Alberto Hernández <ahernandez@moval.es>
* Eduardo Iniesta <einiesta@moval.es>
* Jesús Martínez <jmartinez@moval.es>
* Miguel Mora <mmora@moval.es>
* Miguel Ángel Rodríguez <marodriguez@moval.es>
* Juanu Sandoval <jsandoval@moval.es>
* Salvador Sánchez <ssanchez@moval.es>
* Jorge Vera <jvera@moval.es>

Maintainer
----------

.. image:: https://services.moval.es/static/images/logo_moval_small.png
   :target: http://moval.es
   :alt: Moval Agroingeniería

This module is maintained by Moval Agroingeniería.
