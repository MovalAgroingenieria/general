# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
from datetime import timedelta
from odoo import models, fields, api


class MeasurementDevice(models.Model):
    _inherit = 'mdm.measurement.device'

    device_age = fields.Integer(
        string='device_age',
        compute='_compute_device_age',
        store=False
    )

    @api.one
    @api.depends('installation_date')
    def _compute_device_age(self):
        self.device_age = 0
        if self.installation_date:
            today = fields.Date.from_string(fields.Date.today())
            installation_date = fields.Date.from_string(self.installation_date)

            days = (today - installation_date).days
            self.device_age = days if days > 0 else 0

