# -*- coding: utf-8 -*-
# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Laboratory Analysis for Waters: SALZ Remote Control',
    'summary': 'Base module used for enabling the retrieval of measurements '
               'from remote measuring devices on SALZ Endpoint',
    'version': '10.0.1.1.1',
    'category': 'Laboratory Analysis for Waters',
    'website': 'https://www.moval.es',
    'author': 'Moval Agroingeniería',
    'license': 'AGPL-3',
    'depends': [
        'law_water_quality_remotecontrol',
        'cron_daylight_saving_time_resistant',
    ],
    'data': [
        'views/law_measuring_device_view.xml',
        'views/law_measuring_config_setting_view.xml',
        'views/law_measuring_device_measurement_view.xml',
        'views/law_water_quality_menus.xml',
    ],
    'application': False,
    'installable': True,
}
