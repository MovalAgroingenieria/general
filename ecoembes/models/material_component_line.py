# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MaterialComponentLine(models.Model):
    _name = "material.component.line"
    _description = "Material Component Line"
    _order = "product_tmpl_id, material_id, submaterial_id, id"

    product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        string="Product Template",
        required=True,
        ondelete="cascade",
    )

    material_id = fields.Many2one(
        comodel_name="product.material",
        string="Material",
        required=True,
    )

    submaterial_id = fields.Many2one(
        comodel_name="product.submaterial",
        string="Submaterial",
        required=True,
    )

    submaterial_type_id = fields.Many2one(
        comodel_name="product.submaterial.type",
        string="Submaterial Type",
        required=True,
        help="Specific type within the selected submaterial "
        "(carries the per-kg fee, etc.).",
    )

    weight_grams = fields.Float(
        string="Weight (g)",
        digits=(16, 2),
        help="Component weight in grams used for fee calculations.",
    )

    # -----------------------------
    # Onchange helpers (UI domains)
    # -----------------------------

    @api.onchange("material_id")
    def _onchange_material_id(self):
        """When a material is chosen, restrict submaterials to that material."""
        for line in self:
            if line.material_id:
                # Reset dependent fields
                line.submaterial_id = False
                line.submaterial_type_id = False
            else:
                line.submaterial_id = False
                line.submaterial_type_id = False

    @api.onchange("submaterial_id")
    def _onchange_submaterial_id(self):
        """When a submaterial is chosen, restrict types to that submaterial."""
        for line in self:
            if line.submaterial_id:
                line.submaterial_type_id = False
            else:
                line.submaterial_type_id = False

    @api.onchange("submaterial_type_id")
    def _onchange_type_id(self):
        """Selecting a type auto-fills submaterial and material."""
        for line in self:
            st = line.submaterial_type_id
            if st:
                line.submaterial_id = st.submaterial_id
                line.material_id = (
                    st.submaterial_id.material_id if st.submaterial_id else False
                )
            else:
                line.submaterial_id = False
                line.material_id = False

    # --------------
    # Validations
    # --------------

    @api.constrains("weight_grams")
    def _check_weight_non_negative(self):
        for rec in self:
            if rec.weight_grams and rec.weight_grams < 0.0:
                raise ValidationError(
                    self.env._("Weight (g) must be greater than or equal to 0.")
                )

    # --------------
    # Display
    # --------------

    @api.depends(
        "product_tmpl_id", "material_id", "submaterial_id", "submaterial_type_id"
    )
    def _compute_display_name(self):
        """Readable label: '<Product>: Material / Submaterial / Type'."""
        for record in self:
            name_parts = [
                record.product_tmpl_id.display_name or "",
                record.material_id.name or "",
                record.submaterial_id.name or "",
                record.submaterial_type_id.name or "",
            ]
            record.display_name = (
                f"{name_parts[0]}: {name_parts[1]} / {name_parts[2]} / {name_parts[3]}"
            )
