.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

===========================
Remote Control - SCADA Mula
===========================

Integration module for importing sensor readings from SCADA Mula MariaDB database with automatic hydrological year database switching.

The SCADA Mula database system has a specific structure where data is distributed across multiple databases based on hydrological years:

* **Database naming**: ``mula_YYYY_YY`` (e.g., mula_2025_26)
* **Hydrological year period**: September 1st 00:00:00 - August 31st 23:59:59
* **Examples**:
  * mula_2025_26 → September 1, 2025 to August 31, 2026
  * mula_2024_25 → September 1, 2024 to August 31, 2025
  * mula_2026_27 → September 1, 2026 to August 31, 2027

Each database contains tables with sensor readings. The structure is flexible, allowing different tables with configurable field names.

Example table: ``estacion_meteorologica``

* **EstacionNr**: Weather station ID (device identifier)
* **FechaHora**: Timestamp with milliseconds
* **VelocidadViento**: Wind speed measurement
* **DireccionViento**: Wind direction measurement
* **Temperatura**: Temperature measurement
* **Humedad**: Humidity measurement
* **PrecipitacionDiaria**: Daily precipitation measurement
* **RadiacionSolar**: Solar radiation measurement

Configuration
=============

Connection Parameters
---------------------

Configure the MariaDB connection in the Remotecontrol record:

.. code-block:: json

    {
        "driver_name": "MariaDB",
        "host": "192.168.1.100",
        "port": 3306,
        "database_prefix": "mula",
        "user": "username",
        "password": "password",
        "charset": "utf8mb4"
    }

**Required fields:**

* ``driver_name``: Database driver (MariaDB, MySQL)
* ``host``: Database server IP or hostname
* ``port``: Database port (default: 3306)
* ``database_prefix``: Base name for databases (e.g., "mula")
* ``user``: Database username
* ``password``: Database password
* ``charset``: Character encoding (recommended: utf8mb4)

Device Configuration
--------------------

For each sensor you want to import:

1. Create a **Measurement Device** (MDM Device)
2. Set the **remotecontrol** field to "SCADA Mula"

Sensor Configuration
--------------------

For each device, create a **Measurement Sensor** (MDM Sensor) and configure the
**remotecontrol_params** field:

.. code-block:: json

    {
        "table": "estacion_meteorologica",
        "device_field": "EstacionNr",
        "device_id": 0,
        "date_field": "FechaHora",
        "value_field": "Temperatura",
        "start_date": "2025-09-01"
    }

**Required fields:**

* ``table``: Name of the table containing sensor data
* ``device_field``: Column name for the device identifier (e.g., "EstacionNr")
* ``device_id``: Device identifier value (e.g., 0, 1, 2...)
* ``date_field``: Column name for the timestamp (e.g., "FechaHora")
* ``value_field``: Column name for the sensor reading (e.g., "Temperatura", "VelocidadViento")

**Optional fields:**

* ``start_date``: Initial date for importing readings (YYYY-MM-DD format)

The system will automatically:

* Determine which database(s) to query based on date ranges
* Query the specified table using the configured field names
* Filter by device_id and date range
* Convert timestamps from Europe/Madrid timezone to UTC
* Handle multi-database queries when date ranges span multiple hydrological years
* Import all non-null values

Example: Wind Speed Sensor
---------------------------

.. code-block:: json

    {
        "table": "estacion_meteorologica",
        "device_field": "EstacionNr",
        "device_id": 0,
        "date_field": "FechaHora",
        "value_field": "VelocidadViento"
    }

Example: Humidity Sensor from Different Device
-----------------------------------------------

.. code-block:: json

    {
        "table": "estacion_meteorologica",
        "device_field": "EstacionNr",
        "device_id": 1,
        "date_field": "FechaHora",
        "value_field": "Humedad"
    }

Usage
=====

Export Sensors Catalog
----------------------

Before configuring sensors, you can export the complete catalog from the current SCADA database:

1. Go to the Remotecontrol record for SCADA Mula
2. Execute the action "Export sensors catalog"
3. Download the generated CSV file from attachments

The CSV contains all available tables and columns from the current hydrological year database with sample values, helping you identify:

* Available table names
* Column names and data types
* Sample values for each field

Use this CSV to identify which tables and fields to configure in Odoo sensors.

Manual Execution
----------------

1. Go to the Remotecontrol record for SCADA Mula
2. Select the procedure "SCADA Mula: Daily Sync"
3. Click "Execute procedure"

Automatic Execution
-------------------

Configure a scheduled action (cron) to run the procedure automatically:

1. Go to Settings > Technical > Automation > Scheduled Actions
2. Create a new action
3. Set the model to ``remotecontrol.procedure``
4. Set the function to ``execute``
5. Set the domain to filter the SCADA Mula procedure
6. Configure the execution interval (e.g., daily)

Hydrological Year Logic
========================

Automatic Database Selection
-----------------------------

The system automatically determines which database(s) to query based on:

* Last reading date from the sensor (if available)
* Current date
* Configured start_date (if specified)

**Single hydrological year query:**

If all dates fall within the same hydrological year, a single database is queried.

**Multi-year query:**

If the date range spans multiple hydrological years, the system:

1. Splits the date range into segments by hydrological year
2. Queries each relevant database separately
3. Combines all results
4. Deduplicates readings based on sensor_id + measurement_time

**Example multi-year scenario:**

Importing data from August 2025 to October 2025:

1. Query ``mula_2024_25`` for August 1-31, 2025
2. Query ``mula_2025_26`` for September 1 - October 31, 2025
3. Merge results into Odoo

SQL Query Generated
===================

For a temperature sensor configured with table ``estacion_meteorologica``, device_field ``EstacionNr``,
device_id ``0``, date_field ``FechaHora``, and value_field ``Temperatura``,
the system generates:

.. code-block:: sql

    SELECT `Temperatura` AS value, `FechaHora` AS timestamp
    FROM `estacion_meteorologica`
    WHERE `EstacionNr` = 0
      AND `FechaHora` >= '2025-09-01 00:00:00'
      AND `FechaHora` <= '2026-01-08 23:59:59'
      AND `Temperatura` IS NOT NULL
    ORDER BY `FechaHora` ASC

The date range is automatically calculated based on the last imported reading or configured start_date.
All field names are fully configurable via sensor parameters.

Technical Features
==================

* **Hydrological Year Detection**: Automatically calculates database name from dates
* **Multi-Database Support**: Seamlessly queries across multiple databases when needed
* **Flexible Schema**: Fully configurable table names and field names
* **Timezone Conversion**: Automatic conversion from Europe/Madrid to UTC
* **UTF-8 Encoding**: Full Unicode support with utf8mb4 charset
* **CSV Export**: Generates sensor catalog from current hydrological year database
* **Audit Trail**: Creates JSON attachments with detailed import results
* **MariaDB/MySQL Compatible**: Works with both MariaDB and MySQL databases
* **Prepared Statements**: Uses parameterized queries for security and performance

Adding New Tables
=================

The module is designed to be flexible and support any table structure. To add a new table:

1. Export the sensors catalog to see available tables and columns
2. Create a new sensor in Odoo
3. Configure remotecontrol_params with the appropriate field names:
   * ``table``: The table name
   * ``device_field``: Column that identifies the device
   * ``device_id``: The device identifier value
   * ``date_field``: Column containing the timestamp
   * ``value_field``: Column containing the measurement value

**No code changes are required** - the system dynamically builds queries based on your configuration.

Example: Adding a New Pressure Table
-------------------------------------

If the database has a table ``presion_tuberias`` with columns:

* ``ID_Tuberia`` (device identifier)
* ``Momento`` (timestamp)
* ``Presion_Bar`` (pressure value)

Configure the sensor as:

.. code-block:: json

    {
        "table": "presion_tuberias",
        "device_field": "ID_Tuberia",
        "device_id": 5,
        "date_field": "Momento",
        "value_field": "Presion_Bar"
    }

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

.. image:: https://raw.githubusercontent.com/MovalAgroingenieria/public-assets/master/logos/logo_moval_small.png
   :target: http://moval.es
   :alt: Moval Agroingeniería

This module is maintained by Moval Agroingeniería.
