# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields


class IrModel(models.Model):
    _inherit = 'ir.model'

    available_on_app = fields.Boolean(
        string='Available on App',
        default=False,)


class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    available_on_app = fields.Boolean(
        string='Available on App',
        default=False,)
