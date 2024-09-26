# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, fields, api, _

class ProjectProject(models.Model):
    _inherit = "project.project"
    
    
    excluded_from_attendance_report = fields.Boolean(
        string="Excluded from attendance report",
        default=False,
        required=True,
        help="Enable to excluded from attendance report.")
