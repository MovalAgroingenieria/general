# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductMaterial(models.Model):
    _name = "product.material"
    _description = "Product Material"
    _order = "code"
    _rec_name = "name"

    code = fields.Char(
        required=True,
        index=True,  # helpful for uniqueness & lookups
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
            code = (record.code or "").strip()
            if not code:
                # Keep required=True semantics explicit in case of RPC misuse
                raise ValidationError(self.env._("Code is required."))
            if not code.isdigit():
                # Allow leading zeros (e.g., '01', '08') as in your data file
                raise ValidationError(self.env._("Code must contain only digits."))

    @api.model_create_multi
    def create(self, vals_list):
        # normalize input (strip spaces in code)
        for vals in vals_list:
            if "code" in vals and isinstance(vals["code"], str):
                vals["code"] = vals["code"].strip()
            if "name" in vals and isinstance(vals["name"], str):
                vals["name"] = vals["name"].strip()
        return super().create(vals_list)

    def write(self, vals):
        # normalize input (strip spaces in code)
        if "code" in vals and isinstance(vals["code"], str):
            vals["code"] = vals["code"].strip()
        if "name" in vals and isinstance(vals["name"], str):
            vals["name"] = vals["name"].strip()
        return super().write(vals)
