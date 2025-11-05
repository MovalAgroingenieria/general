# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductMaterial(models.Model):
    _name = "product.material"
    _description = "Product Material"
    _order = "code"

    code = fields.Char(
        string="Code",
        required=True,
    )

    name = fields.Char(
        string="Material",
        required=True,
        translate=True,
    )

    _sql_constraints = [
        ("code_unique", "unique(code)", "Code must be unique."),
    ]

    @api.constrains("code")
    def _check_code_format(self):
        for record in self:
            if not record.code.isdigit():
                raise ValidationError("Code must contain only digits.")
