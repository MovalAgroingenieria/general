# Copyright 2026 Moval
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrDepartment(models.Model):
    _inherit = "hr.department"

    x_generic_warn_pct = fields.Float(
        string="Generic Warning Threshold (%)",
        help="Department-specific generic allocation warning threshold.",
    )
    x_generic_issue_pct = fields.Float(
        string="Generic Issue Threshold (%)",
        help="Department-specific generic allocation issue threshold.",
    )
