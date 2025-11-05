# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class Stage(models.Model):
    _inherit = "crm.stage"
    
    is_new = fields.Boolean(
        string="Is New",
        default=False,
        help="Indicates if the stage is new.",
    )
