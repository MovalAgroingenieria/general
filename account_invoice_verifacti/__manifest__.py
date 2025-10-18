# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Account Invoice Verifacti Integration',
    'version': '10.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Integration with Verifacti API for Spanish invoice verification',
    'author': 'Moval Agroingeniería',
    'website': 'http://www.moval.es',
    "license": "AGPL-3",
    'depends': [
        'account',
        'l10n_es',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/verifacti_security.xml',
        'views/res_config_settings_views.xml',
        'views/account_journal_views.xml',
        'views/account_invoice_views.xml',
        'views/verifacti_nif_views.xml',
        'views/verifacti_log_views.xml',
        'views/menuitems.xml',
        'data/ir_cron.xml',
        'report/invoice_report_template.xml',
    ],
    'external_dependencies': {
        'python': ['requests', 'qrcode', 'PIL'],
    },
    'application': False,
    'installable': True,
}



