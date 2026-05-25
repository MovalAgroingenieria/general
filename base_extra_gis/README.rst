.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

=====================
Base-Extra-Gis Module
=====================

Abstract module to get the geometries of PostGis tables, for all possible
geometries, and other functionalities.

Description
===========

This module creates the model "simplegis.model". It is an abstract model,
that add methods to process the PostGis geometries and other functionalities.

For example, a model with a GIS link that can inherit from "simplegis.model"
will have a no-persistent calculated field with the geometries assigned to the
GIS link.

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
