# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Base Meteo",
    "summary": "Generate meteorological raster products (COG) by "
               "interpolating MDM sensor readings.",
    "version": "10.0.0.3.0",
    "category": "Geospatial",
    "website": "http://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "depends": [
        "base",
        "mdm_sensor_management",
        "mdm_sensor_management_gis",
    ],
    "external_dependencies": {
        "python": ["PIL", "numpy"],
        "bin": ["gdal_translate", "gdaladdo"],
    },
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/meteo_aggregation_data.xml",
        "data/meteo_variable_data.xml",
        "data/meteo_product_data.xml",
        "data/meteo_cron.xml",
        "views/meteo_aggregation_views.xml",
        "views/meteo_variable_views.xml",
        "views/meteo_raster_views.xml",
        "views/meteo_product_views.xml",
        "views/meteo_menu.xml",
    ],
    "installable": True,
}
