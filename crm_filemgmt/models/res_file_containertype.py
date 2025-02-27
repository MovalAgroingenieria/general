# -*- coding: utf-8 -*-
# 2021 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields


class ResFileContainerType(models.Model):
    _name = 'res.file.containertype'
    _description = "Type of containers"

    name = fields.Char(
        string='Name',
        required=True,
        index=True,)

    description = fields.Char(
        string='Description',)

    notes = fields.Html(
        string='Notes')