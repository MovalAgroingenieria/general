# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    employee_role_assignment_ids = fields.One2many(
        related='employee_id.role_assignment_ids',
        string='Role Assignments',
        readonly=True,
    )
