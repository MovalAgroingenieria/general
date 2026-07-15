.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

======================
Spain SII OCA Extended
======================

Description
===========
This module extends ``l10n_es_aeat_sii_oca``.

It preserves the original SII identifier generation logic and adds a specific
behavior for partners whose VAT is ``/``.

In that case, the module treats the identifier as not available and generates
the AEAT payload with:

* ``IDType`` = ``06``
* ``ID`` = ``NO_DISPONIBLE``

This avoids generating an empty identifier such as:

* ``IDType`` = ``04``
* ``ID`` = ``""``


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
* Jose Mendez <jjmendez@moval.es>
* Miguel Mora <mmora@moval.es>
* Juanu Sandoval <jsandoval@moval.es>
* Salvador Sánchez <ssanchez@moval.es>
* Jorge Vera <jvera@moval.es>

Maintainer
----------
.. image:: https://raw.githubusercontent.com/MovalAgroingenieria/public-assets/master/logos/logo_moval_small.png
   :target: http://moval.es
   :alt: Moval Agroingeniería

This module is maintained by **Moval Agroingeniería**.
