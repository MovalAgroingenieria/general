RemoteControl: IkosTech
=======================

Remotecontrol for IkosTech soil monitoring devices and weather stations.

IkosTech provides comprehensive hydrological, soil, and weather data via REST API.

Features
--------

* X-API-Key authentication (no OAuth)
* Fetches historical data per device/serial
* Configurable date range fetching (1 month chunks to prevent timeouts)
* Supports multiple sensors per device (humidity, temperature, conductivity, etc.)
* Automatic cron scheduling (e.g., daily at 6 AM)
* Integration with MDM (Measurement Data Management)
* Full audit trail with per-sensor diagnostics

Installation
------------

Install the module and configure a remotecontrol device with:

* **Device level**: ``remotecontrol_params`` with ``start_date`` (e.g., "2026-01-01")
* **Sensor level**: ``remotecontrol_params`` with ``field`` (e.g., "hsuelo", "tsuelo", "tamb", etc.)

Usage
-----

1. Configure connection_params on the remote control record:

   .. code-block:: json

     {
       "api_key": "your_ikostech_api_key"
     }

2. Create a ``mdm.measurement.device`` with IkosTech remotecontrol type
3. Add the API key to connection_params
4. In each ``mdm.measurement.device``, set ``remotecontrol_params`` with ``start_date``
5. Add sensors with ``remotecontrol_params`` containing ``field`` (the JSON field name from IkosTech)
6. Set procedure schedule (e.g., daily at 6 AM)
7. Enable procedure cron
8. Readings will be auto-fetched and stored in ``mdm.measurement.device.sensor.reading``

Available Fields
----------------

IkosTech devices provide these measurement fields per reading:

* ``fecha``: Timestamp (YYYY-MM-DD HH:MM:SS)
* ``hamb``: Ambient humidity (%)
* ``tamb``: Ambient temperature (°C)
* ``hsuelo``: Soil humidity (%)
* ``tsuelo``: Soil temperature (°C)
* ``conductividad``: Soil conductivity (mS/cm)
* ``radiacion``: Solar radiation (W/m²)
* ``radiacion_umol``: PAR radiation (μmol/m²/s)
* ``radiacion_global``: Global solar radiation (W/m²)
* ``dpv``: Vapor pressure deficit (kPa)
* ``bateria``: Battery level (%)
* ``calidad``: Signal quality (0-4)

Contributors
------------

* Moval Agroingeniería
