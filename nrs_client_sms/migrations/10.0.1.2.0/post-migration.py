# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from odoo import api, SUPERUSER_ID


_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Migration script to clean up orphaned access rules and access controls
    for the transient model nrs.schedule.wizard.
    This script removes Access controls (ir.model.access) linked to the model
    """

    _logger.info('Cleaning up orphaned access rules for nrs.schedule.wizard')

    # Initialize the environment to use ORM methods
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Search for the 'ir.model' record corresponding to our transient model
    model_obj = env['ir.model'].search(
        [('model', '=', 'nrs.schedule.wizard')], limit=1)

    if model_obj:
        # Find and delete access controls (ir.model.access)
        access_controls = env['ir.model.access'].search(
            [('model_id', '=', model_obj.id)])
        if access_controls:
            _logger.info(
                'Deleting %s access control(s).', len(access_controls))
            access_controls.unlink()
        else:
            _logger.info('No access controls found for nrs.schedule.wizard.')

        _logger.info(
            'Cleanup of access rules for nrs.schedule.wizard completed.')
    else:
        _logger.info(
            'Model nrs.schedule.wizard not found in ir.model. '
            'No cleanup needed.')
