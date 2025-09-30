# -*- coding: utf-8 -*-
# Copyright 2019 Solvos Consultoría Informática (<http://www.solvos.es>)
# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Maintenance Stock',
    'summary': 'Links maintenance requests to stock',
    'version': '10.0.1.0.1',
    'category': 'Warehouse',
    'website': 'http://www.moval.es',
    'author': 'Moval Agroingeniería',
    'license': 'AGPL-3',
    'depends': [
        'base_maintenance_config',
        'maintenance',
        'maintenance_form_buttons',
        'stock',
    ],
    'data': [
        'views/maintenance_equipment_views.xml',
        'views/maintenance_request_views.xml',
        'views/maintenance_settings_view.xml',
        'views/stock_move_views.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
}
