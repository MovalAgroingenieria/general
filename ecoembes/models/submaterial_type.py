# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SubmaterialType(models.Model):
    _name = "submaterial.type"
    _description = "Submaterial Type"

    code = fields.Char(
        string="Code",
        required=True,
        copy=False,
    )

    name = fields.Char(
        string="Name",
        required=True,
        translate=True,
    )

    submaterial_id = fields.Many2one(
        comodel_name="product.submaterial",
        string="Submaterial",
        required=True,
    )

    fee_per_kg = fields.Float(
        string="Fee €/kg",
        digits=(16, 5),
        help="Tarifa oficial de contribución al SCRAP por kilogramo",
    )

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Code must be unique.'),
    ]
