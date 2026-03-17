# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    'name': 'Remote Control - SCADA Mula',
    'summary': 'Integration with SCADA Mula MariaDB database (hydrological year support)',
    'version': '10.0.1.0.2',
    'category': 'Tools',
    'author': 'Moval Agroingenieria',
    'website': 'https://moval.es',
    'license': 'AGPL-3',
    'depends': [
        'base_remotecontrol',
    ],
    'data': [
        'data/data.xml',
    ],
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'auto_install': False,
}
