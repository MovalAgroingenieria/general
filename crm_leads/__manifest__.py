# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'CRM Leads',
    'summary': 'Leads management for CRM',
    'version': '14.0.1.1.0',
    'category': 'Customer Relationship Management',
    'website': 'https://www.moval.es',
    'author': 'Moval Agroingeniería',
    'license': 'AGPL-3',
    'depends': [
        'crm',
    ],
    'data': [
        'views/crm_lead_views.xml',
    ],
    'application': True,
    'installable': True,
}
