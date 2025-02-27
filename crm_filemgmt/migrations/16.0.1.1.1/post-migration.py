# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# @INFO: To migrate the state of the files to the new stage field is necessary
#        to add the field state (deleted after migration).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    state_to_stage = {
        '01_draft': 'Draft',
        '02_inprogress': 'In Progress',
        '03_closed': 'Closed',
    }
    for state, stage_name in state_to_stage.items():
        stage = env['res.file.stage'].search([('name', '=', stage_name)])
        files = env['res.file'].search([('state', '=', state)])
        if len(files) > 0:
            files.write({'stage_id': stage.id})
    cancelled_files = env['res.file'].search([('is_cancelled', '=', True)])
    if len(cancelled_files) > 0:
        cancelled_files.write({'active': False})
