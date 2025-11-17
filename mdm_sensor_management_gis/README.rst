.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

===================================
MDM Sensor Management GIS Extension
===================================

This module extends the MDM Sensor Management system with comprehensive GIS
(Geographic Information System) visualization capabilities. It enables spatial
representation of measurement devices, custom symbology for device categories,
and interactive map-based monitoring of sensor networks.

Key Features
============

* **GIS Device Visualization**: Display measurement devices on interactive maps
* **Category Symbology**: Configure custom GeoJSON styles for each device category
* **Legend Symbology**: Define visual legends for map layers
* **Style Preview**: Real-time preview of category styles
* **Device Availability Control**: Toggle device visibility in GIS mode
* **Auto-refresh Configuration**: Configurable refresh intervals for device data
* **Random Style Generator**: Quick style generation for categories

Technical Overview
==================

The module enhances existing MDM models with GIS-specific functionality:

**Measurement Device Category**
  * ``geojson_style``: GeoJSON style definition for map rendering
  * ``geojson_style_preview``: Computed field for style preview
  * ``legend_symbology``: Legend configuration for the category
  * ``available_for_gis_devices``: Toggle for GIS device mode visibility
  * ``action_randomize_style()``: Generate random styles automatically

**Measurement Device**
  * ``available_for_gis_devices``: Individual device visibility control

**Settings Model**
  * ``default_gis_devices_refresh_interval``: Global refresh interval configuration

GeoJSON Style Format
====================

Category styles use the GeoJSON specification for feature styling:

.. code-block:: json

    {
        "color": "#3388ff",
        "weight": 2,
        "opacity": 0.8,
        "fillColor": "#3388ff",
        "fillOpacity": 0.4,
        "radius": 8
    }

Common Style Properties
-----------------------

* **color**: Stroke color (hex or named color)
* **weight**: Stroke width in pixels
* **opacity**: Stroke opacity (0-1)
* **fillColor**: Fill color for polygons/circles
* **fillOpacity**: Fill opacity (0-1)
* **radius**: Radius for point markers (in pixels)

Legend Symbology Format
=======================

Legend configuration defines how categories appear in map legends:

.. code-block:: json

    {
        "label": "Flow Meters",
        "icon": "circle",
        "color": "#3388ff"
    }

Installation
============

This module depends on:

* ``mdm_sensor_management`` - Core MDM functionality

The module will automatically extend existing measurement device and category
views with GIS-specific fields and actions.

Configuration
=============

After installing the module:

1. Navigate to **MDM > Configuration > Settings**
2. Configure the GIS refresh interval (in seconds)
3. Go to **MDM > Configuration > Device Categories**
4. For each category:

   * Enable "Available in Devices Mode" if desired
   * Define GeoJSON style or use "Randomize Style" action
   * Configure legend symbology
   * Preview the style in the form view

5. Optionally, control individual device visibility in GIS mode

Usage
=====

Category Style Configuration
----------------------------

1. Open a measurement device category
2. Go to the "Viewer" tab
3. Enter GeoJSON style definition or click "Randomize Style"
4. The style preview updates automatically
5. Configure legend symbology for map legends
6. Save the category

Device Visibility Control
--------------------------

**Category Level**: Control visibility for all devices in a category

1. Edit device category
2. Check/uncheck "Available in Devices Mode"
3. All devices in this category will inherit the setting

**Device Level**: Override category setting for individual devices

1. Edit measurement device
2. Check/uncheck "Available for GIS Devices"
3. This overrides the category setting

GIS Settings
------------

1. Navigate to **MDM > Configuration > Settings**
2. Adjust "GIS Devices Refresh Interval" (default: 30 seconds)
3. Click "Apply" to save

Known Issues / Roadmap
======================

* Style validation is not enforced (invalid GeoJSON will cause rendering errors)
* No built-in style editor (manual JSON editing required)
* Legend symbology format is not standardized

Credits
=======

* Moval Agroingeniería S.L.

Contributors
------------
* Guillermo Amante <gamante@moval.es>
* Samuel Fernández <sfernandez@moval.es>
* Pablo García <pgarcia@moval.es>
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

.. image:: https://services.moval.es/static/images/logo_moval_small.png
   :target: http://moval.es
   :alt: Moval Agroingeniería

This module is maintained by Moval Agroingeniería.
