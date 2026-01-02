.. |badge1| image:: https://img.shields.io/badge/license-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

|badge1|

================
SMS Alternatives
================

**Table of contents**

.. contents::
   :local:

Description
===========

This module adds a configuration option to select which SMS service should be
used.

SMS provider modules are expected to extend the selection field with their own
entry and provide the corresponding configuration settings.

For developers
~~~~~~~~~~~~~~

To add your SMS service to the selection field, extend ``res.config.settings``
and use ``selection_add``:

.. code-block:: python

   from odoo import fields, models

   class ResConfigSettings(models.TransientModel):
       _inherit = "res.config.settings"

       sms_service = fields.Selection(
           selection_add=[("yoursms_service", "Your SMS")],
       )

Credits
=======

Authors
~~~~~~~

* Moval Agroingeniería S.L.

Contributors
~~~~~~~~~~~~

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

Maintainers
~~~~~~~~~~~

This module is maintained by Moval Agroingeniería.

.. image:: https://services.moval.es/static/images/logo_moval_small.png
   :alt: Moval Agroingeniería
   :target: http://moval.es
