# -*- coding: utf-8 -*-
# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Complaints Channel",
    "summary": "Management of the complaints channel.",
    "version": '16.0.1.0.0',
    "category": "Complaints and Infringements Management",
    "website": "http://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "depends": [
        "contacts",
        "mail",
        "html_text",
        "website",
        # "web_tree_image",
        # "website_form_builder",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/cim_complaint_type_data.xml",
        "data/cim_link_type_data.xml",
        "wizards/wizard_reject_complaint_view.xml",
        "wizards/wizard_resolve_complaint_view.xml",
        "wizards/wizard_complainant_data_view.xml",
        "views/cim_complaints_channel_menus.xml",
        "views/res_cim_config_settings_view.xml",
        "views/cim_complaint_type_view.xml",
        "views/cim_complaint_view.xml",
        "views/cim_link_type_view.xml",
        "views/complainant_templates.xml",
        "reports/cim_complaint_tracking_code_report.xml",
        "reports/cim_complaint_communication_report.xml",
        "data/mail_template_data.xml",
    ],
    "installable": True,
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "application": True,
}
