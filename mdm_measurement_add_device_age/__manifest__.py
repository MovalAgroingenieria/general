# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'MDM Measurement Management Device: Add Device Age',
    'summary': 'Measurement Devices Management: '
               'Add Device Age',
    'version': '10.0.1.1.0',
    'category': 'Tools',
    'website': 'https://www.moval.es',
    'author': 'Moval Agroingeniería',
    'license': 'AGPL-3',
    'depends': [
        'mdm_sensor_management',
    ],
    'data': [
        'security/security.xml',
        'views/measurement_device_views.xml',
    ],
    'application': False,
    'installable': True,
}
