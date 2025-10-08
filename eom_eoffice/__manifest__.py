# -*- coding: utf-8 -*-
# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Electronic Office",
    "summary": "Electronic Office with authentication based on digital "
               "certificate.",
    "version": '10.0.1.0.0',
    "category": "Electronic Offices Management",
    "website": "http://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "depends": [
        "document",
        "eom_authdnie",
        "web_tree_image",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/ir_cron_data.xml",
        "views/resources.xml",
        "views/eom_electronicfile_view.xml",
        "views/eom_digitalregister_view.xml",
        "views/eom_digitalregister_templates.xml",
        "views/eom_electronicfile_templates.xml",
        "views/res_eom_config_settings_view.xml",
        "views/eom_electronicfile_communication_view.xml",
        "reports/report_notification.xml",
        "data/mail_template_data.xml",
        "reports/report_instance.xml",
    ],
    "installable": True,
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "application": True,
}
