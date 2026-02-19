.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

============================
RemoteControl: Spherag Atlas
============================

Integration with Spherag Atlas API for retrieving sensor data and historical measurements.

Features
========

* Authentication via Spherag login endpoint (token per execution, not persisted)
* Support for hierarchical model: System → Atlas → AtlasElement → ChartType
* Discovery endpoints to list devices, sensors, and available metrics
* Historical data retrieval with configurable time windows
* Adaptive parser supporting multiple API response formats
* Incremental data synchronization based on last reading timestamp
* Automated daily sync procedure

Configuration
=============

Remote Control Setup
---------------------

1. Go to *Base Remote Control → Remote Controls*
2. Create or configure the Spherag remote control
3. Set connection parameters (JSON):

.. code-block:: json

    {
      "username": "your-email@example.com",
      "password": "your-password",
      "api_core_url": "https://apicore.spherag.com",
      "system_id": 1401
    }

Device Configuration
--------------------

In each measurement device (``mdm.measurement.device``), configure the ``remotecontrol_params`` field with:

.. code-block:: json

    {
      "system_id": 1401,
      "imei": "865648060417847",
      "start_date": "2025-01-01"
    }

* **system_id**: Spherag system identifier
* **imei**: Atlas device identifier (physical device)
* **start_date**: Default start date for data retrieval (optional)

Sensor Configuration
--------------------

In each sensor (``mdm.measurement.device.sensor``), configure the ``remotecontrol_params`` field with:

.. code-block:: json

    {
      "atlas_element_id": 4260,
      "chart_type": 8,
      "start_date": "2025-01-01"
    }

* **atlas_element_id**: Sensor identifier within the Atlas device
* **chart_type**: Metric type identifier (e.g., temperature, humidity)
* **start_date**: Overrides device start date if provided (optional)

Usage
=====

Discovery Workflow
------------------

1. Execute the procedure **"Spherag: Import Devices and Metrics"**
2. This will:

   * Authenticate and obtain access token
   * List all Atlas devices in the system
   * For each device, list all AtlasElements (sensors)
   * For each sensor, list available ChartTypes (metrics)
   * Generate a JSON attachment with the complete structure

3. Use the generated JSON to identify the correct IDs for configuring devices and sensors in Odoo

Daily Synchronization
---------------------

1. Configure devices and sensors with the appropriate IDs (see Configuration section)
2. Execute the procedure **"Spherag: Daily Sync"**
3. This will:

   * Authenticate and obtain access token
   * Build a plan of sensors to synchronize
   * For each sensor, retrieve historical data since last reading
   * Parse and store readings in ``mdm.measurement.device.sensor.reading``
   * Generate an audit JSON attachment with synchronization results

API Endpoints
=============

Authentication
--------------

* **POST** ``https://api.spherag.com/Authentication/Login``

  * Request: ``{"username": "user@example.com", "password": "password"}``
  * Response: ``{"accessToken": {"token": "JWT_TOKEN", "expiration": "..."}``

Discovery
---------

* **GET** ``https://apicore.spherag.com/systems/{systemId}/Atlas``

  * Returns list of Atlas devices with their IMEI

* **GET** ``https://apicore.spherag.com/systems/{systemId}/Atlas/{imei}/AtlasElements``

  * Returns list of sensors (elements) within a device

* **GET** ``https://apicore.spherag.com/AtlasElement/Charts/{atlasElementId}``

  * Returns available chart types (metrics) for a sensor

Historical Data
---------------

* **GET** ``https://apicore.spherag.com/ccrr/{systemId}/Atlas/{imei}/AtlasElement/{atlasElementId}/monitoring?ChartType={chartType}&StartDate={timestamp_ms}&EndDate={timestamp_ms}``

  * Returns historical readings for a specific metric
  * Timestamps in epoch milliseconds
  * Header required: ``Authorization: Bearer {access_token}``

Technical Notes
===============

* Authentication is required for each execution (token is not persisted)
* Only ``accessToken`` is used (``refreshToken`` is ignored)
* Timestamps are in milliseconds (epoch format)
* Supports two response formats:

  * Format A: Flat structure with direct field values
  * Format B: Nested structure with data array

* Readings are identified by ``(sensor_id, measurement_time)`` for idempotent upserts
* Rate limiting: 0.5 seconds between requests

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
