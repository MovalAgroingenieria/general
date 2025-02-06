# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class ProjectType(models.Model):
    _inherit = "project.type"
    _order = "sequence"

    sequence = fields.Integer(
        string="Sequence",
        required=True,
    )
