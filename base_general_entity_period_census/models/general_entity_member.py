# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class GeneralEntityMember(models.Model):
    _inherit = "general.entity.member"

    default_shares = fields.Float(
        string="Shares",
        digits=(12, 3),
        help="Default shares value applied when generating census lines "
        "for this member from active members. Not used when copying "
        "from a previous period.",
    )
