.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

=============================
Remote Control - SCADA Abarán
=============================

Integration module for importing sensor readings from legacy SCADA Abarán SQL Server database.

The SCADA Abarán database has a specific structure where each table uses a composite
primary key formed by three columns:

* **REMOTA**: Remote station ID
* **IDENTIFICADOR**: Sensor identifier within the station
* **TIPO_INFORMACION**: Type of information (0=instantaneous, 1=accumulated, etc.)

Each table also contains:

* **FECHA**: Timestamp with milliseconds
* **VALOR**: Numeric value of the reading

Common tables: ``Historico_Caudalimetros``, ``Historico_Presion``, ``Historico_Nivel``,
``Historico_Caudal_Instantaneo``

Configuration
=============

Connection Parameters
---------------------

Configure the SQL connection in the Remotecontrol record:

.. code-block:: json

    {
        "driver": "FreeTDS",
        "server": "192.168.1.100",
        "port": 1433,
        "database": "scada_abaran",
        "user": "username",
        "password": "password",
        "tds_version": "7.0"
    }

Device Configuration
--------------------

For each sensor you want to import:

1. Create a **Measurement Device** (MDM Device)
2. Set the **remotecontrol** field to "SCADA Abarán"

Sensor Configuration
--------------------

For each device, create a **Measurement Sensor** (MDM Sensor) and configure the
**remotecontrol_params** field:

.. code-block:: json

    {
        "table": "Historico_Caudalimetros",
        "remota": 109,
        "identificador": 1,
        "tipo_informacion": 0,
        "value_field": "VALOR",
        "time_field": "FECHA",
        "start_date": "2025-01-01"
    }

**Required fields:**

* ``table``: Name of the historical table (e.g., Historico_Caudalimetros)
* ``remota``: Remote station ID number
* ``identificador``: Sensor identifier within the station
* ``tipo_informacion``: Information type code (0=instantaneous, 1=accumulated, etc.)
* ``value_field``: Column name containing the sensor readings (usually "VALOR")
* ``time_field``: Column name containing the timestamp (usually "FECHA")

**Optional fields:**

* ``start_date``: Initial date for importing readings (YYYY-MM-DD format)

The system will automatically:

* Query the specified table using the composite key
* Filter by the date range (from last imported reading or start_date)
* Convert timestamps from Europe/Madrid timezone to UTC
* Import all non-null values

Usage
=====

Export Sensors Catalog
----------------------

Before configuring sensors, you can export the complete catalog from the SCADA database:

1. Go to the Remotecontrol record for SCADA Abarán
2. Execute the action "Export sensors catalog"
3. Download the generated CSV file from attachments

The CSV contains all available sensors with:

* REMOTA, TIPO_ELEMENTO, IDENTIFICADOR, TIPO_INFORMACION (for sensor configuration)
* DEVICE_NAME, DEVICE_DESCRIPTION (sensor information)
* SENSOR_NAME (measurement type description)

Use this CSV to identify which sensors to configure in Odoo.

Manual Execution
----------------

1. Go to the Remotecontrol record for SCADA Abarán
2. Select the procedure "SCADA Abaran: Daily Sync"
3. Click "Execute procedure"

Automatic Execution
-------------------

Configure a scheduled action (cron) to run the procedure automatically:

1. Go to Settings > Technical > Automation > Scheduled Actions
2. Create a new action
3. Set the model to ``remotecontrol.procedure``
4. Set the function to ``execute``
5. Set the domain to filter the SCADA Abarán procedure
6. Configure the execution interval (e.g., daily)

Available Historical Tables
===========================

The module supports the following SCADA tables:

* HISTORICO_ASPIRACIONES
* HISTORICO_BALSAS
* HISTORICO_BOMBAS
* HISTORICO_CAUDALIMETROS
* HISTORICO_CORRIENTE
* HISTORICO_ENERGIA_ACTIVA
* HISTORICO_ENERGIA_REACTIVA
* HISTORICO_FACTOR_POTENCIA
* HISTORICO_POTENCIA_ACTIVA
* HISTORICO_POTENCIA_REACTIVA
* HISTORICO_TEMPERATURA
* HISTORICO_TRANSMISORES_PRESION
* HISTORICO_VALVULAS

All tables follow the same composite key structure (REMOTA, IDENTIFICADOR, TIPO_INFORMACION).

SQL Query Generated
===================

For a sensor configured with table ``Historico_Caudalimetros``, remota ``109``,
identificador ``1``, tipo_informacion ``0``, value_field ``VALOR``, and time_field ``FECHA``,
the system generates:

.. code-block:: sql

    SELECT VALOR, FECHA
    FROM Historico_Caudalimetros
    WHERE REMOTA = 109
      AND IDENTIFICADOR = 1
      AND TIPO_INFORMACION = 0
      AND FECHA >= '2025-01-01 00:00:00.000'
      AND FECHA <= '2025-01-31 23:59:59.999'
      AND VALOR IS NOT NULL
    ORDER BY FECHA ASC

The date range is automatically calculated based on the last imported reading.
The field names (VALOR, FECHA) are configurable via value_field and time_field parameters.

Technical Features
==================

* **Composite Primary Key Support**: Handles complex 3-field primary keys (REMOTA, IDENTIFICADOR, TIPO_INFORMACION)
* **Timezone Conversion**: Automatic conversion from Europe/Madrid to UTC
* **Millisecond Handling**: Properly processes SQL Server datetime format with milliseconds
* **UTF-8 Encoding**: Correctly handles Spanish characters (ñ, á, é, í, ó, ú)
* **CSV Export**: Generates sensor catalog from SCADA database tables (ELEMENTOS_INSTALACION + INFORMACION_HIDRAULICA)
* **Audit Trail**: Creates JSON attachments with import results

Credits
=======

 * Moval Agroingeniería S.L.

Contributors
------------
* Guillermo Amante <gamante@moval.es>
* Juan José Bautista <jjbautista@moval.es>
* Samuel Fernández <sfernandez@moval.es>
* Pablo García <pgarcia@moval.es>
* Alberto Hernández <ahernandez@moval.es>
* Eduardo Iniesta <einiesta@moval.es>
* Jesús Martínez <jmartinez@moval.es>
* José Javier Méndez <jjmendez@moval.es>
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

