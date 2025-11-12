# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ProductSubMaterial(models.Model):
    _name = "product.submaterial"
    _description = "Submaterial"
    _rec_name = "name"
    _order = "material_id, code, id"

    code = fields.Char(
        required=True,
        help="Internal submaterial code (must be unique).",
    )

    name = fields.Char(
        required=True,
        translate=True,
    )

    material_id = fields.Many2one(
        comodel_name="product.material",
        string="Material",
        required=True,
        ondelete="restrict",
    )

    _sql_constraints = [
        ("code_unique", "unique(code)", "Code must be unique."),
    ]

    @api.depends("name", "material_id.name")
    def _compute_display_name(self):
        """Format display name as 'Material - Submaterial'."""
        for record in self:
            if record.material_id:
                record.display_name = f"{record.material_id.name} - {record.name}"
            else:
                record.display_name = record.name
