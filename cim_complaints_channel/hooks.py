# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Initialize the "sequence_complaint_code_id" param (Many2one).
    try:
        sequence_coding_code_id = env.ref(
            'cim_complaints_channel.sequence_complaint_code').id
    except (Exception, ):
        sequence_coding_code_id = 0
    if sequence_coding_code_id > 0:
        env['ir.config_parameter'].set_param(
            'cim_complaints_channel.sequence_complaint_code_id',
            sequence_coding_code_id)
    # Initialize the rest of the params.
    env['ir.config_parameter'].set_param(
        'cim_complaints_channel.length_tracking_code', 8)
    env['ir.config_parameter'].set_param(
        'cim_complaints_channel.acknowledgement_period', 7)
    env['ir.config_parameter'].set_param(
        'cim_complaints_channel.automatic_email_state', False)
    env['ir.config_parameter'].set_param(
        'cim_complaints_channel.automatic_email_validate_com', False)
    env['ir.config_parameter'].set_param(
        'cim_complaints_channel.automatic_email_complainant_com', False)
    env['ir.config_parameter'].set_param(
        'cim_complaints_channel.notice_period', 15)
    env['ir.config_parameter'].set_param(
        'cim_complaints_channel.deadline', 3)
    env['ir.config_parameter'].set_param(
        'cim_complaints_channel.deadline_extended', 6)
    # Set the fields "website_form_access" and "website_form_label" of the
    # "ir.model" model: allow the use of a form on the website to submit
    # complaints.
    models = env['ir.model']
    model_complaint = models.search([('model', '=', 'cim.complaint')])
    if model_complaint:
        model_complaint = model_complaint[0]
        model_complaint.write({
            'website_form_access': True,
            'website_form_label': 'Add complaint form', })
    # Idem for the "cim.complaint.communication" model.
    model_complaint_communication = models.search(
        [('model', '=', 'cim.complaint.communication')])
    if model_complaint_communication:
        model_complaint_communication = model_complaint_communication[0]
        model_complaint_communication.write({
            'website_form_access': True,
            'website_form_label': 'Add communication form', })


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    try:
        env.cr.savepoint()
        env.cr.execute("""
            DELETE FROM ir_default
            WHERE model='res.config.settings'""")
        env.cr.commit()
    except (Exception,):
        env.cr.rollback()
