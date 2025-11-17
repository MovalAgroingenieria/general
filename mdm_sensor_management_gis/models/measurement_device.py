# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MeasurementDevice(models.Model):
    _inherit = 'mdm.measurement.device'

    available_for_gis_devices = fields.Boolean(
        string='Available in Devices Mode',
        default=True,
        help='Make this device available in GIS devices visualization mode',
    )
