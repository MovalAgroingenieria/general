.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

==================================
RemoteControl: Regaber SKYplatform
==================================

Integration with the Regaber SKYplatform REST API v2.6 for retrieving water
meter counter readings (SKYreg and SKYmeter NB-IoT devices).

Features
========

* Token-based authentication (Bearer, valid 1 day)
* Discovery of the element tree (`GET /TreeNode`)
* Last counter value retrieval for SKYreg water meters, SKYreg hydrant
  water meters, and SKYmeter NB-IoT water meters
* Designed to feed ``wua.reading`` records via the WUA integration module

Configuration
=============

Remote Control Setup
--------------------

1. Go to *Base Remote Control → Remote Controls*
2. Create or configure the Regaber SKYplatform remote control
3. Set connection parameters (JSON):

.. code-block:: json

    {
      "username": "user@example.com",
      "password": "your-password"
    }

Waterconnection Configuration (via ``wua_remotecontrol_rest_regaber``)
-----------------------------------------------------------------------

In each ``wua.waterconnection``, set the *Regaber TreeNode ID* to the
``Id`` value returned by ``GET /TreeNode`` for the corresponding water
meter element, and choose the *Regaber Device Type* matching the element
type in SKYplatform.

Available Procedures
====================

* **Regaber: Get Tree Nodes** — Authenticates and downloads the full element
  tree; creates a JSON attachment for reference.
* **Regaber: Get Last Readings** — Authenticates and fetches the latest
  counter value for each element in ``bag['target_nodes']``.  Used
  internally by the WUA reading import.

API Reference
=============

Base URL: ``https://api.skyplatform.matwatertech.com``

Authentication::

    POST /Token
    Content-Type: application/x-www-form-urlencoded

    username=...&password=...&grant_type=password

Relevant endpoints::

    GET /TreeNode
    GET /SKYreg/WaterMeter/LastValue/?id={treeNodeId}
    GET /SKYreg/Hydrant/WaterMeter/LastValue/?id={treeNodeId}
    GET /SKYmeterNBIoT/WaterMeter/LastValue/?id={treeNodeId}

Credits
=======

 * Moval Agroingeniería S.L.

Contributors
------------
* Guillermo Amante <gamante@moval.es>
* Samuel Fernández <sfernandez@moval.es>
* Alberto Hernández <ahernandez@moval.es>
* Jesús Martínez <jmartinez@moval.es>
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
