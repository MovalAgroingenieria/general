# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class DecaLine(models.Model):
    _name = "deca.line"
    _description = "DECA Goods Line"

    deca_id = fields.Many2one(
        "deca.document",
        string="DECA",
        required=True,
        ondelete="cascade",
        index=True,
    )
    name = fields.Char(string="Description", required=True)
    quantity = fields.Float(default=1.0)
    uom_name = fields.Char(string="Unit of Measure")
    weight_kg = fields.Float(string="Weight (kg)")
