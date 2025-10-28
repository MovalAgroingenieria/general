# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields


class IrModuleModule(models.Model):
    _inherit = 'ir.module.module'

    available_on_app = fields.Boolean(
        string='Available on App',
        default=False,
    )
