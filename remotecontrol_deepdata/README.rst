.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

========================
RemoteControl: DeepData
========================

Integration with DeepData REST API (v1.0.3) for catalog synchronization and
measure import using the ``base_remotecontrol`` engine.

Features
========

* Cookie-based authentication (``JSESSIONID``) via ``GET /rest/login``
* Catalog synchronization procedure (structural pre-requisite):
  ``getIdiomas`` → ``getInstalaciones`` → ``getCategorias`` →
  ``getPuntosMedida`` → ``getVariables``
* Measure import procedure via ``POST /rest/getMedidas``
* Support for hierarchical model: Installation → Measure Point → Variable
* Automatic re-login on session expiry (``REST0003``)
* Automatic date range splitting on ``REST0012`` (range too large)
* Retry with backoff on transient errors (``REST0013``)
* Idempotent upserts: ``(sensor_id, measurement_time)`` as composite key
* Audit JSON attachments generated after each execution
* Sensors grouped by installation for efficient batched API calls
* Timezone handling per installation

Configuration
=============

Remote Control Setup
--------------------

1. Go to *Base Remote Control → Remote Controls*
2. Create or configure the DeepData remote control
3. Set connection parameters (JSON):

.. code-block:: json

    {
      "username": "your_user",
      "password": "your_password",
      "timezone": "Europe/Madrid"
    }

* **username**: DeepData login user
* **password**: DeepData login password
* **timezone**: Default timezone for date handling (IANA format, can be overridden per installation)

Device Configuration
--------------------

In each measurement device (``mdm.measurement.device``), configure the ``remotecontrol_params`` field with:

**Minimum (required):**

.. code-block:: json

    {
      "installation_id": 1
    }

**Full (with optional fields):**

.. code-block:: json

    {
      "installation_id": 1,
      "timezone": "Europe/Madrid",
      "start_date": "2025-01-01"
    }

* **installation_id** *(required)*: DeepData installation identifier
* **timezone** *(optional)*: IANA timezone for this installation. Defaults to the value in ``connection_params``
* **start_date** *(optional)*: Start date for first data retrieval. Defaults to Jan 1st of current year

Sensor Configuration
--------------------

In each sensor (``mdm.measurement.device.sensor``), configure the ``remotecontrol_params`` field with:

**Minimum (required):**

.. code-block:: json

    {
      "measure_point_id": 10,
      "variable_id": 100
    }

**Full (with optional fields):**

.. code-block:: json

    {
      "measure_point_id": 10,
      "variable_id": 100,
      "start_date": "2025-01-01"
    }

* **measure_point_id** *(required)*: DeepData measure point identifier
* **variable_id** *(required)*: DeepData variable identifier
* **start_date** *(optional)*: Overrides device start date if provided

Usage
=====

Catalog Sync (Discovery Workflow)
---------------------------------

1. Execute the procedure **"DeepData: Catalog Sync"**
2. This will:

   * Authenticate and obtain JSESSIONID
   * Retrieve languages, installations, categories, measure points and variables
   * Build the full hierarchy: installations → measure points → variables
   * Generate a JSON attachment with the complete catalog structure

3. Use the generated JSON to identify the correct IDs for configuring devices and sensors in Odoo

Measure Import (Daily Synchronization)
--------------------------------------

1. Configure devices and sensors with the appropriate IDs (see Configuration section)
2. Execute the procedure **"DeepData: Import Measures"**
3. This will:

   * Authenticate and obtain JSESSIONID
   * Build a plan of sensors to synchronize, grouped by installation
   * For each installation, call ``POST /rest/getMedidas`` with the configured measure points and variables
   * Parse and store readings in ``mdm.measurement.device.sensor.reading``
   * Handle session expiry, range limits and transient errors automatically
   * Generate an audit JSON attachment with import results

Procedures
==========

+-----------------------------------+----------------------------------+
| Procedure                         | Steps                            |
+===================================+==================================+
| DeepData: Catalog Sync            | 1. Login                         |
|                                   | 2. Sync Catalog                  |
+-----------------------------------+----------------------------------+
| DeepData: Import Measures         | 1. Login                         |
|                                   | 2. Get Devices (Plan)            |
|                                   | 3. Get Measures                  |
+-----------------------------------+----------------------------------+

API Endpoints
=============

Authentication
--------------

* **GET** ``/rest/login?user=…&password=…``

  * Returns ``JSESSIONID`` cookie in ``Set-Cookie`` header
  * All subsequent requests must include ``Cookie: JSESSIONID=<value>``

Catalog
-------

* **GET** ``/rest/getIdiomas`` — List available languages
* **GET** ``/rest/getInstalaciones`` — List installations
* **GET** ``/rest/getCategorias`` — List variable categories
* **GET** ``/rest/getPuntosMedida`` — List measure points per installation
* **GET** ``/rest/getVariables`` — List variables per measure point

Measures
--------

* **POST** ``/rest/getMedidas``

  * Request body: JSON with ``startDate``, ``endDate`` (format ``YYYY-MM-DD HH:mm:SS``) and ``instalaciones`` array
  * Response: ``medidas`` array with ``date`` (timestamp) and ``listValue`` entries containing ``idInstallation``, ``idMeasurePoint``, ``idVariable``, ``value``

Error Handling
==============

+-----------+---------------------------+-----------------------------------+
| Code      | Description               | Automatic Action                  |
+===========+===========================+===================================+
| REST0003  | Session expired           | Re-login and retry (max 3 times)  |
+-----------+---------------------------+-----------------------------------+
| REST0012  | Range too large           | Split date range in half, retry   |
+-----------+---------------------------+-----------------------------------+
| REST0013  | Server processing error   | Backoff wait + retry              |
+-----------+---------------------------+-----------------------------------+

Technical Notes
===============

* Authentication is required for each execution (JSESSIONID is not persisted)
* Timestamps in request use format ``YYYY-MM-DD HH:mm:SS``
* Readings are identified by ``(sensor_id, measurement_time)`` for idempotent upserts
* Rate limiting: 0.5 seconds between installation requests
* Sensors are grouped by installation to minimize API calls

Credits
=======

* Moval Agroingeniería S.L.

Contributors
------------
* Guillermo Amante <gamante@moval.es>
* César Andrés Sanchez <candres@moval.es>
* Juan José Bautista <jjbautista@moval.es>
* Samuel Fernández <sfernandez@moval.es>
* Alberto Hernández <ahernandez@moval.es>
* Eduardo Iniesta <einiesta@moval.es>
* Jesús Martínez <jmartinez@moval.es>
* José Javier Méndez <jjmendez@moval.es>
* Miguel Mora <mmora@moval.es>
* Juanu Sandoval <jsandoval@moval.es>
* Salvador Sánchez <ssanchez@moval.es>
* Jorge Vera <jvera@moval.es>

Maintainer
----------

.. image:: https://services.moval.es/static/images/logo_moval_small.png
   :target: http://moval.es
   :alt: Moval Agroingeniería

This module is maintained by Moval Agroingeniería.
