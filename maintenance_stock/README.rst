
.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

=================
Maintenance Stock
=================

.. note::
   Backport migration of original module Maintenance Stock of version 12.0


Usage
=====

Once installed, first you should enable consumptions for a certain equipment
and filling a default warehouse for the picking operations:

.. figure:: https://raw.githubusercontent.com/OCA/maintenance/12.0/maintenance_stock/static/description/equipment.png
   :alt: Kanban view
   :width: 600 px

Then, for every mainteance request of this equipment, *Picking List* button
allows us to make consumptions, that will be picking documents with their own
sequence:

.. figure:: https://raw.githubusercontent.com/OCA/maintenance/12.0/maintenance_stock/static/description/request-1.png
   :alt: Kanban view
   :width: 600 px

.. figure:: https://raw.githubusercontent.com/OCA/maintenance/12.0/maintenance_stock/static/description/pick-1.png
   :alt: Kanban view
   :width: 600 px

By default, the origin location for this operations will be the stock location
for the default warehouse, and destination a new *Consumptions* location, that
will not compute for stock inventory, like e.g. partner locations:

.. figure:: https://raw.githubusercontent.com/OCA/maintenance/12.0/maintenance_stock/static/description/move-line.png
   :alt: Kanban view
   :width: 600 px

From both request and equipment forms these stock operations and *Product Moves*
are available.

Return operations are also enabled, and will be linked to the request and
equipment as well:

.. figure:: https://raw.githubusercontent.com/OCA/maintenance/12.0/maintenance_stock/static/description/pick-2.png
   :alt: Kanban view
   :width: 600 px

Known issues / Roadmap
======================

* Product standard list. Enable defining product standard lists (at least,
  product and quantity per line), and link them with equipments. Then, every
  maintenance request could select one of them and automatically fill the
  product and quantity list.


Credits
=======

Authors of original 12.0
~~~~~~~~~~~~~~~~~~~~~~~~

* Solvos

Authors
~~~~~~~

* Moval Agroingeniería S.L.

Contributors
------------

* David Alonso <david.alonso@solvos.es> [original 12.0]
* Samuel Fernández <sfernandez@moval.es>
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

.. image:: https://raw.githubusercontent.com/MovalAgroingenieria/public-assets/master/logos/logo_moval_small.png
   :target: http://moval.es
   :alt: Moval Agroingeniería

This module is maintained by Moval Agroingeniería.

Maintainers of original 12.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This module is maintained by the OCA.

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

This module is part of the `OCA/maintenance <https://github.com/OCA/maintenance/tree/12.0/maintenance_project>`_ project on GitHub.

You are welcome to contribute. To learn how please visit https://odoo-community.org/page/Contribute.
