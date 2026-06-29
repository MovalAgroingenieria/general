# -*- coding: utf-8 -*-
# 2026 Moval Agroingenieria
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import SUPERUSER_ID, api


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    xmlids = [
        'remotecontrol_avamet.remotecontrol_avamet',
        'remotecontrol_avamet.'
        'mdm_measurement_device_sensor_type_avamet_temp_min',
        'remotecontrol_avamet.'
        'mdm_measurement_device_sensor_type_avamet_temp_avg',
        'remotecontrol_avamet.'
        'mdm_measurement_device_sensor_type_avamet_temp_max',
        'remotecontrol_avamet.'
        'mdm_measurement_device_sensor_type_avamet_hum_min',
        'remotecontrol_avamet.'
        'mdm_measurement_device_sensor_type_avamet_hum_avg',
        'remotecontrol_avamet.'
        'mdm_measurement_device_sensor_type_avamet_hum_max',
        'remotecontrol_avamet.'
        'mdm_measurement_device_sensor_type_avamet_pres_min',
        'remotecontrol_avamet.'
        'mdm_measurement_device_sensor_type_avamet_pres_avg',
        'remotecontrol_avamet.'
        'mdm_measurement_device_sensor_type_avamet_pres_max',
        'remotecontrol_avamet.'
        'mdm_measurement_device_sensor_type_avamet_wind_dir',
        'remotecontrol_avamet.'
        'mdm_measurement_device_sensor_type_avamet_wind_avg',
        'remotecontrol_avamet.'
        'mdm_measurement_device_sensor_type_avamet_wind_gust',
        'remotecontrol_avamet.'
        'mdm_measurement_device_sensor_type_avamet_rain',
        'remotecontrol_avamet.'
        'mdm_measurement_device_sensor_uom_avamet_celsius',
        'remotecontrol_avamet.'
        'mdm_measurement_device_sensor_uom_avamet_percent',
        'remotecontrol_avamet.mdm_measurement_device_sensor_uom_avamet_hpa',
        'remotecontrol_avamet.mdm_measurement_device_sensor_uom_avamet_kmh',
        'remotecontrol_avamet.mdm_measurement_device_sensor_uom_avamet_mm',
        'remotecontrol_avamet.mdm_measurement_device_sensor_uom_avamet_deg',
    ]
    for xmlid in xmlids:
        record = env.ref(xmlid, raise_if_not_found=False)
        if record:
            record.with_context(force_unlink=True).unlink()
