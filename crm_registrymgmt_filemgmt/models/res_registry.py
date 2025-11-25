# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class ResRegistry(models.Model):
    _inherit = 'res.registry'

    file_id = fields.Many2one(
        'res.file',
        string='File'
    )
