# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    cmr_tractor_license_plate_id = fields.Many2one(
        string="Tractor license plate",
        comodel_name="cmr.license.plate",
        copy=False,
    )
    cmr_semi_trailer_license_plate_id = fields.Many2one(
        string="Semi-trailer license plate",
        comodel_name="cmr.license.plate",
        copy=False,
    )
