.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

==================================
Remote Control - SCADA Abarán New
==================================

Integration module for importing sensor readings from SCADA Abarán MariaDB database
with native connection (non-ODBC).

This module connects to a MariaDB database where each device has its own table
containing sensor readings with timestamps in DD/MM/YYYY HH:MM format.

Database Structure
==================

Each device has its own table with the following structure:

* **ID_MEDIDA**: Auto-increment primary key
* **FECHA_HORA**: Timestamp in DD/MM/YYYY HH:MM format (e.g., "19/11/2025 13:45")
* **Sensor columns**: CAUDAL, VOLUMEN, PRESION, etc. (varies by device)

Example table ``a1_2``::

    ID_MEDIDA | FECHA_HORA       | CAUDAL | VOLUMEN | PRESION
    ----------+------------------+--------+---------+--------
            1 | 19/11/2025 13:45 |   12.5 |  1250.0 |    2.3
            2 | 19/11/2025 14:00 |   11.8 |  1261.8 |    2.2
            3 | 19/11/2025 14:15 |   13.2 |  1275.0 |    2.4

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
        "database": "scada_abaran_new",
        "user": "scada_user",
        "password": "password",
        "charset": "utf8mb4"
    }

**Important**: Use ``"driver_name": "MariaDB"`` for native connection (NOT ODBC).

Device Configuration
--------------------

For each device you want to import:

1. Create a **Measurement Device** (MDM Device)
2. Set the **remotecontrol** field to "SCADA Abarán New"
3. Configure the **remotecontrol_params** field with the device table name:

.. code-block:: json

    {
        "table_name": "a1_2"
    }

**Required fields:**

* ``table_name``: Name of the device table in MariaDB (e.g., "a1_2", "b3_1")

Sensor Configuration
--------------------

For each device, create a **Measurement Sensor** (MDM Sensor) and configure the
**remotecontrol_params** field:

.. code-block:: json

    {
        "datetime_column": "FECHA_HORA",
        "value_column": "CAUDAL",
        "start_date": "2025-01-01"
    }

**Required fields:**

* ``datetime_column``: Column name for timestamp (usually "FECHA_HORA")
* ``value_column``: Column name for sensor value (e.g., "CAUDAL", "VOLUMEN", "PRESION")

**Optional fields:**

* ``start_date``: Initial date for importing readings (YYYY-MM-DD format)

Date Format
-----------

**IMPORTANT**: All dates in the database use a **FIXED format**:

* **Format**: DD/MM/YYYY HH:MM (e.g., "19/11/2025 13:45")
* **Timezone**: Europe/Madrid (automatically converted to UTC)
* **Not configurable**: This format is hardcoded in the system

Do **NOT** include ``datetime_format`` in sensor configuration - it's always DD/MM/YYYY HH:MM.

Usage
=====

Export Table Schema
-------------------

Before configuring sensors, export the database schema to understand available
tables and columns:

1. Go to the Remotecontrol record for SCADA Abarán New
2. Click on "Actions" → "SCADA Abarán New: Export table schema"
3. Download the CSV file from attachments
4. Review the available tables and their columns
5. Use this information to configure device and sensor parameters

The CSV contains:

* **TABLE_NAME**: Name of each table (use for device ``table_name``)
* **COLUMN_NAME**: Name of each column (use for ``datetime_column`` and ``value_column``)
* **DATA_TYPE**: SQL data type
* **SAMPLE_VALUES**: Example values from the first row

Daily Synchronization
---------------------

To import sensor readings:

1. Go to the Remotecontrol record for SCADA Abarán New
2. Click on "Procedures" → "SCADA Abarán New: Daily Sync"
3. Click "Execute"

This procedure will:

1. Build a plan of all configured devices and sensors
2. Query each device table for new readings
3. Convert timestamps from DD/MM/YYYY HH:MM (Europe/Madrid) to UTC
4. Import readings into Odoo (avoiding duplicates)
5. Generate a detailed JSON audit attachment

You can schedule this procedure to run automatically via cron job.

Manual Actions
--------------

You can also run individual actions:

* **Export table schema**: Export database schema to CSV
* **Get devices (plan)**: Build execution plan for all sensors
* **Get readings**: Import readings (requires plan from previous action)

Technical Features
==================

* **Native MariaDB Connection**: Uses mysql-connector-python or pymysql (NOT ODBC)
* **Fixed Date Format**: Always DD/MM/YYYY HH:MM (hardcoded, not configurable)
* **Timezone Conversion**: Automatic Europe/Madrid → UTC conversion
* **UTF-8 Encoding**: Full Unicode support with utf8mb4 charset
* **Per-Device Tables**: Each device has its own table structure
* **Flexible Columns**: Configurable datetime and value column names
* **CSV Schema Export**: Generates complete database schema documentation
* **Audit Trail**: Creates JSON attachments with detailed import results
* **Error Handling**: Robust error handling with detailed error messages
* **Upsert Logic**: Avoids duplicate readings (based on sensor + timestamp)

Troubleshooting
===============

Connection Issues
-----------------

* **Connection refused**: Check host, port, firewall, and VPN
* **Login failed**: Verify credentials and database name
* **Driver not found**: Install mysql-connector-python or pymysql

.. code-block:: bash

    pip install mysql-connector-python
    # or
    pip install pymysql

Configuration Issues
--------------------

* **No data returned**: Verify ``table_name``, ``datetime_column``, and ``value_column`` in configuration
* **Table not found**: Use "Export table schema" action to verify table names
* **Column not found**: Use "Export table schema" action to verify column names

Date/Time Issues
----------------

* **Date parsing errors**: Ensure database uses DD/MM/YYYY HH:MM format exactly
* **Wrong timezone**: System expects Europe/Madrid timezone, converts to UTC automatically

Other Issues
------------

* **Encoding errors**: Ensure charset is set to utf8mb4 in connection params
* **Empty CSV export**: Check database connection and permissions

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
