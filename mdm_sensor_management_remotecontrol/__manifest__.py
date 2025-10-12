# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'MDM Sensor Management: Remotecontrol Integration',
    'summary': 'Measurement Devices and Sensors Management: '
               'Add Remotecontrol Integration',
    'version': '10.0.1.1.0',
    'category': 'Tools',
    'website': 'https://www.moval.es',
    'author': 'Moval Agroingeniería',
    'license': 'AGPL-3',
    'depends': [
        'mdm_sensor_management',
        'base_remotecontrol',
    ],
    'data': [
        'security/security.xml',
        'views/measurement_device_views.xml',
        'views/measurement_device_sensor_views.xml',
        'views/measurement_device_sensor_reading_views.xml',
        'views/remotecontrol_views.xml',
    ],
    'application': False,
    'installable': True,
}
