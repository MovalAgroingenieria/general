.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
	 :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
	 :alt: License: AGPL-3

============================================================
Base Language Export Multi-Language Module
============================================================

Export module translations for several loaded languages in a single download.

Description
===========

This module extends the standard Odoo translation export wizard with a
multiple-language selector and a Select all button.

* Select all includes active languages enabled for translation.
* Selecting a single module automatically selects those languages.
* One selected language produces the standard PO, CSV or TGZ download.
* Several selected languages produce a ZIP archive containing one export per
  language in the chosen format, plus an empty POT translation template.
* The POT template is named after the selected module, or modules.pot when
  exporting several modules or all modules. It always uses PO format,
  regardless of the selected export format.
* Leaving Languages empty preserves the original Language selector, including
  the empty translation template option.

The module selection is respected in every exported file.

Usage
=====

1. Open Settings > Translations > Import / Export > Export Translation.
2. Select the module or modules to export.
3. Select the desired languages, or click Select all.
4. Choose the file format and click Export.
5. Download the generated file. For multiple languages, extract the ZIP to
   obtain the translations and the POT template.

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