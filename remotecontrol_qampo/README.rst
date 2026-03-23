====================
RemoteControl: Qampo
====================

Integration with the `Qampo <https://qampo.es>`_ IoT platform for
agricultural sensor data (soil humidity, weather, etc.).

This module provides a ``remotecontrol`` record with pre-configured
actions and procedures to:

* **Sync Catalog**: Fetch all Qampo devices (stations) and their
  published variables, auto-creating ``mdm.measurement.device`` and
  ``mdm.measurement.device.sensor`` records.

* **Import Readings**: Retrieve sensor readings via the Qampo
  ``getValues`` endpoint and upsert them into
  ``mdm.measurement.device.sensor.reading``.

Configuration
=============

1. Install the module.
2. Go to *Remote Controls* and open the **Qampo** record.
3. Set the ``connection_params`` JSON with your API key::

    {
      "apikey": "your_api_key_here",
      "timezone": "Europe/Madrid"
    }

4. Run the **Qampo: Catalog Sync** procedure to fetch devices and
   auto-create sensors.
5. Run the **Qampo: Import Readings** procedure (or schedule it via
   cron) to start importing sensor data.

API Reference
=============

* Base URL: ``https://api.qampo.es/apiv2/api``
* Authentication: ``apikey`` header on every request.
* ``GET /devices``: List all stations with sensors and published variables.
* ``GET /getValues?nodeid=X&ts_start=MS&ts_end=MS``: Get readings
  (timestamps in milliseconds, values as strings).
* ``GET /health``: API health check.

Dependencies
============

* ``base_remotecontrol``
* ``mdm_sensor_management_remotecontrol``
