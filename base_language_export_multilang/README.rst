.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

==========================================
Base Language Export Multi-Language Module
==========================================

Export module translations for several loaded languages in a single download.

Description
===========

Extends the standard translation export wizard to select several loaded
languages for module exports in a single operation. Selecting one module
automatically selects all active languages, and a Select all button is available.

When several languages are selected, the download is a ZIP archive containing
one file per language in the chosen format (PO, CSV or TGZ), plus an empty POT
translation template. Selecting one language or leaving the selection empty
preserves the standard export behavior. Odoo 18 model exports are unchanged.


Usage
=====

#. Enable developer mode and open Settings > Translations > Export Translation.
#. Keep the Module export type and select the apps to export.
#. Select the desired languages or click Select all to select all active languages.
#. Choose PO, CSV or TGZ and click Export.
#. Download the ZIP archive when several languages are selected, or the standard
   translation file when only one language is selected.

Clear the Languages selection and choose New Language to export only an empty
template. For model exports, use the standard Language field.


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