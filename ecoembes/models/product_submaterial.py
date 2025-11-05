# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProductSubMaterial(models.Model):
    _name = "product.submaterial"
    _description = "Submaterial"

    code = fields.Char(
        string="Code",
        required=True,
    )

    name = fields.Char(
        string="Submaterial",
        required=True,
        translate=True,
    )

    material_id = fields.Many2one(
        comodel_name="product.material",
        string="Material",
        required=True,
    )

    _sql_constraints = [
        ("code_unique", "unique(code)", "Code must be unique."),
    ]

    def name_get(self):
        res = []
        for obj in self:
            if obj.material_id:
                res.append((obj.id, f"{obj.material_id.name} - {obj.name}"))
            else:
                res.append((obj.id, obj.name))
        return res
