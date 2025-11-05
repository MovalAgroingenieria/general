# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models, api


class MaterialComponentLine(models.Model):
    _name = 'material.component.line'
    _description = 'Material Component Line'

    product_tmpl_id = fields.Many2one(
        comodel_name='product.template',
        string='Product Template',
        required=True,
        ondelete='cascade',
    )

    material_id = fields.Many2one(
        comodel_name='product.material',
        string='Material',
        required=True,
    )

    submaterial_id = fields.Many2one(
        comodel_name='product.submaterial',
        string='Submaterial',
        required=True,
    )

    submaterial_type_id = fields.Many2one(
        comodel_name='submaterial.type',
        string='Submaterial Type',
        required=True,
    )

    weight_grams = fields.Float(
        string='Weight (g)',
        digits=(16, 2),
    )

    @api.onchange('material_id')
    def _onchange_material_id(self):
        """Filter submaterials by selected material."""
        for line in self:
            domain = {}
            if line.material_id:
                domain['submaterial_id'] = [
                    ('material_id', '=', line.material_id.id)
                ]
                line.submaterial_id = False
                line.submaterial_type_id = False
            else:
                domain['submaterial_id'] = []
                line.submaterial_id = False
                line.submaterial_type_id = False
            return {'domain': domain}

    @api.onchange('submaterial_id')
    def _onchange_submaterial_id(self):
        """Filter submaterial types by selected submaterial."""
        for line in self:
            domain = {}
            if line.submaterial_id:
                domain['submaterial_type_id'] = [
                    ('submaterial_id', '=', line.submaterial_id.id)
                ]
                line.submaterial_type_id = False
            else:
                domain['submaterial_type_id'] = []
                line.submaterial_type_id = False
            return {'domain': domain}

    @api.onchange('submaterial_type_id')
    def _onchange_type_id(self):
        """Auto-complete material and submaterial from selected type."""
        for line in self:
            if line.submaterial_type_id:
                line.submaterial_id = line.submaterial_type_id.submaterial_id
                line.material_id = \
                    line.submaterial_type_id.submaterial_id.material_id
            else:
                line.submaterial_id = False
                line.material_id = False

    def name_get(self):
        """Improve display of lines in list views or many2one fields."""
        result = []
        for record in self:
            name = f"{record.product_tmpl_id.display_name or ''}: "
            name += f"{record.material_id.name or ''} / "
            name += f"{record.submaterial_id.name or ''} / "
            name += f"{record.submaterial_type_id.name or ''}"
            result.append((record.id, name))
        return result
