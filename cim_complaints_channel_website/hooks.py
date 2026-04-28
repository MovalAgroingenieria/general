# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID

TEMPLATE_XMLIDS = [
    'cim_complaints_channel_website.complaints_channel_page',
    'cim_complaints_channel_website.info_complaints_channel_page',
    'cim_complaints_channel_website.new_complaint_page',
    'cim_complaints_channel_website.new_communication_page',
]

FORM_MODELS = [
    'cim.complaint',
    'cim.complaint.communication',
]


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for xmlid in TEMPLATE_XMLIDS:
        view = env.ref(xmlid, raise_if_not_found=False)
        if view:
            view.unlink()
    for model_name in FORM_MODELS:
        model = env['ir.model'].search([('model', '=', model_name)], limit=1)
        if model:
            model.website_form_access = False
