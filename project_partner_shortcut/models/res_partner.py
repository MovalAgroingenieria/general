# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    project_count = fields.Integer(
        string="Projects",
        compute='_compute_project_count',
    )

    def _compute_project_count(self):
        project = self.env['project.project']
        for partner in self:
            partner.project_count = project.search_count(
                [('partner_id', '=', partner.id)])
