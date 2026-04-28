# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Complaints Channel - Website Page",
    "summary": "Public website landing page for the complaints channel.",
    "version": "10.0.1.0.0",
    "category": "Complaints and Infringements Management",
    "website": "http://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "depends": [
        "cim_complaints_channel",
        "website_form",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/cim_complaints_channel_website_data.xml",
        "data/website_form_config.xml",
        "views/cim_complaints_channel_website_view.xml",
        "views/complaints_channel_page_template.xml",
        "views/new_complaint_template.xml",
        "views/new_communication_template.xml",
        "views/info_complaints_channel_template.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "uninstall_hook": "uninstall_hook",
}
