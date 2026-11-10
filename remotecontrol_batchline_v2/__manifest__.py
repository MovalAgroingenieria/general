# -*- coding: utf-8 -*-
# Copyright 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'RemoteControl: Batchline v2',
    'summary': 'Batchline API-key integration for MDM elements and readings',
    'version': '10.0.1.0.0',
    'category': 'Tools',
    'website': 'http://www.moval.es',
    'author': 'Moval Agroingeniería',
    'license': 'AGPL-3',
    'depends': [
        'base_remotecontrol',
        'mdm_sensor_management_remotecontrol',
        'cron_daylight_saving_time_resistant',
    ],
    'external_dependencies': {'python': ['dateutil']},
    'data': ['data/data.xml'],
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'application': False,
}