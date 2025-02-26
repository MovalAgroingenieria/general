# -*- coding: utf-8 -*-
# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    values = env['ir.default'].sudo()
    # Initialize the "sequence_complaint_code_id" param (Many2one).
    try:
        sequence_coding_code_id = env.ref(
            'eom_eoffice.sequence_electronicfile_code').id
    except (Exception, ):
        sequence_coding_code_id = 0
    if sequence_coding_code_id > 0:
        values.set('res.config.settings',
                   'sequence_electronicfile_code_id',
                   sequence_coding_code_id)
    # Set default config params
    values.set('res.config.settings', 'deadline', 3)
    values.set('res.config.settings', 'notification_deadline', 10)
    values.set('res.config.settings', 'max_size_attachments', 20)


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    try:
        env.cr.savepoint()
        env.cr.execute("""
            DELETE FROM ir_values
            WHERE model='res.config.settings'
            AND name != 'editable_notes'""")
        env.cr.commit()
    except (Exception,):
        env.cr.rollback()
