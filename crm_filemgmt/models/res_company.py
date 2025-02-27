# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models, api


class ResCompany(models.Model):
    _inherit = "res.company"

    file_prefix = fields.Char(
        string='File Prefix',
        size=10,
        company_dependent=True,)
