# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductSubmaterialType(models.Model):
    _name = "submaterial.type"
    _description = "Submaterial Type"
    _order = "code"

    code = fields.Char(
        required=True,
        copy=False,
    )

    name = fields.Char(
        required=True,
        translate=True,
    )

    submaterial_id = fields.Many2one(
        comodel_name="product.submaterial",
        string="Submaterial",
        required=True,
        ondelete="restrict",
    )

    fee_per_kg = fields.Float(
        string="Fee €/kg",
        digits=(16, 5),
        help="Official SCRAP contribution fee per kilogram.",
    )

    _sql_constraints = [
        ("code_unique", "unique(code)", "Code must be unique."),
    ]

    @api.constrains("fee_per_kg")
    def _check_fee_non_negative(self):
        for record in self:
            if record.fee_per_kg and record.fee_per_kg < 0:
                raise ValidationError(record.env._("Fee €/kg cannot be negative."))

    @api.depends("name", "submaterial_id.name", "submaterial_id.material_id.name")
    def _compute_display_name(self):
        """Format display name as 'Material - Submaterial - Type' hierarchy."""
        for record in self:
            if record.submaterial_id and record.submaterial_id.material_id:
                material_name = record.submaterial_id.material_id.name
                submaterial_name = record.submaterial_id.name
                record.display_name = (
                    f"{material_name} - {submaterial_name} - {record.name}"
                )
            elif record.submaterial_id:
                record.display_name = f"{record.submaterial_id.name} - {record.name}"
            else:
                record.display_name = record.name
