# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class MDMConfigSettings(models.TransientModel):
    _name = "mdm.config.settings"
    _inherit = "res.config.settings"
    _description = "MDM Configuration Settings"
