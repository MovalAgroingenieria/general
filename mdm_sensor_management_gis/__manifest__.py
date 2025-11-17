# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'MDM Sensor Management GIS',
    'version': '10.0.1.0.0',
    'category': 'Tools',
    'summary': 'GIS integration for MDM sensor and device management',
    'description': 'Adds GIS visualization capabilities, category styles, '
                   'and symbology configuration for measurement devices.',
    'author': 'Moval Agroingeniería',
    'website': 'https://www.moval.es',
    'license': 'AGPL-3',
    'depends': [
        'mdm_sensor_management',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/mdm_menus.xml',
        'views/measurement_device_category_views.xml',
        'views/measurement_device_views.xml',
        'views/mdm_settings_views.xml',
    ],
    'application': False,
    'installable': True,
}
