# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class MeasurementDevice(models.Model):
    _inherit = 'mdm.measurement.device'

    remotecontrol_id = fields.Many2one(
        string='Remotecontrol',
        comodel_name='remotecontrol',
    )

    remotecontrol_params = fields.Text(
        string='Remotecontrol Parameters',
    )
