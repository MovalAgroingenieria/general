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

    available_for_public_gis_devices = fields.Boolean(
        string='Available in Public Viewer',
        default=False,
    )

    gis_realtime = fields.Boolean(
        string='Real-time in Viewer',
        default=False,
        help='If enabled, the GIS viewer automatically runs the readings '
             'procedure for this device on every refresh cycle, so its '
             'sensor values and symbology update in near real time. '
             'Requires a configured remote control readings procedure.',
    )
