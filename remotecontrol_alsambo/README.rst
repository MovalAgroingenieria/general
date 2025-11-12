.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

========================
Remote Control - Alsambo
========================

Integration module for importing sensor readings from Alsambo SQL database.

The Alsambo database has a specific structure where there is a single table called
**valoresmoval** with:

* One column **fecha** containing the timestamp of the reading
* Multiple other columns, where each column represents a different sensor and contains the sensor's value

Configuration
=============

Connection Parameters
---------------------

Configure the SQL connection in the Remotecontrol record:

.. code-block:: json

    {
        "driver": "SQL Server",
        "server": "192.168.1.100",
        "database": "alsambo_db",
        "uid": "username",
        "pwd": "password"
    }

Device Configuration
--------------------

For each column (sensor) in the **valoresmoval** table that you want to import:

1. Create a **Measurement Device** (MDM Device)
2. Set the **remotecontrol** field to "Alsambo"
3. Set the **name** field to the exact column name in the table

Example: If you have columns ``sensor1``, ``sensor2``, ``sensor3`` in **valoresmoval**,
create three devices with names: ``sensor1``, ``sensor2``, ``sensor3``

Sensor Configuration
--------------------

For each device, create a **Measurement Sensor** (MDM Sensor):

1. Link it to the device
2. Configure the magnitude, unit, etc.

No additional configuration is needed. The system will automatically:

* Read values from the column specified in the device name
* Use the **fecha** column as the timestamp
* Import all readings since the last imported date

Usage
=====

Manual Execution
----------------

1. Go to the Remotecontrol record for Alsambo
2. Select the procedure "Daily import"
3. Click "Execute procedure"

Automatic Execution
-------------------

Configure a scheduled action (cron) to run the procedure automatically:

1. Go to Settings > Technical > Automation > Scheduled Actions
2. Create a new action
3. Set the model to ``remotecontrol.procedure``
4. Set the function to ``execute``
5. Set the domain to filter the Alsambo procedure
6. Configure the execution interval (e.g., daily)

SQL Query Generated
===================

For a device with name ``sensor1``, the system generates:

.. code-block:: sql

    SELECT fecha, sensor1
    FROM valoresmoval
    WHERE fecha >= '2025-01-01 00:00:00'
      AND fecha <= '2025-01-31 23:59:59'
      AND sensor1 IS NOT NULL
    ORDER BY fecha ASC

The date range is automatically calculated based on the last imported reading.

Credits
=======

Contributors
------------

* Moval Agroingeniería <https://moval.es>

Maintainer
----------

This module is maintained by Moval Agroingeniería.
