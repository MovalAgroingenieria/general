# -*- coding: utf-8 -*-
# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Initialize the "sequence_complaint_code_id" param (Many2one).
    try:
        sequence_coding_code_id = env.ref(
            'eom_eoffice.sequence_electronicfile_code').id
    except (Exception, ):
        sequence_coding_code_id = 0
    if sequence_coding_code_id > 0:
        env['ir.config_parameter'].set_param(
            'eom_eoffice.sequence_electronicfile_code_id',
            sequence_coding_code_id)
    # Set default config params
    env['ir.config_parameter'].set_param(
        'eom_eoffice.deadline', 3)
    env['ir.config_parameter'].set_param(
        'eom_eoffice.notification_deadline', 10)
    env['ir.config_parameter'].set_param(
        'eom_eoffice.max_size_attachments', 20)


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    try:
        env.cr.savepoint()
        env.cr.execute("""
            DELETE FROM ir_config_parameter
            WHERE key LIKE 'eom_eoffice.%'""")
        env.cr.commit()
    except (Exception,):
        env.cr.rollback()
