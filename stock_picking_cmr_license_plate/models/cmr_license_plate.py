# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class CmrLicensePlate(models.Model):
    _name = "cmr.license.plate"
    _description = "CMR License Plate"
    _order = "name"

    name = fields.Char(string="License plate", required=True, index=True)
    active = fields.Boolean(default=True)
    note = fields.Char(string="Notes")

    _sql_constraints = [
        ("name_uniq", "unique(name)", "The license plate must be unique."),
    ]
