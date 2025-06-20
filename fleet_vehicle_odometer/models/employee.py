# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class Employee(models.Model):
    _inherit = 'hr.employee'

    employee_cars_count = fields.Integer(groups="fleet.fleet_group_user")
