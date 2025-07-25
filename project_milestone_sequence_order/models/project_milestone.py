# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models


class ProjectMilestone(models.Model):
    _inherit = "project.milestone"
    _order = "project_id,sequence"

    sequence = fields.Integer()

    @api.model
    def create(self, vals):
        seq = self.env["ir.sequence"].next_by_code("project.milestone") or 0
        vals["sequence"] = seq
        return super().create(vals)
