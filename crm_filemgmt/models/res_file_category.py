# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, exceptions, _


class ResFileCategory(models.Model):
    _name = 'res.file.category'
    _description = "Categories of Files"

    name = fields.Char(
        string='Category Name',
        size=50,
        required=True,
        translate=True,
        index=True)

    is_readonly = fields.Boolean(
        string='Read-only Category',
        default=False)

    parent_id = fields.Many2one(
        string='Parent Category',
        comodel_name='res.file.category')

    notes = fields.Html(
        string='Notes')

    file_ids = fields.One2many(
        string='Associated Files',
        comodel_name='res.file',
        inverse_name='category_id')

    number_of_files = fields.Integer(
        string='Files',
        store=True,
        compute='_compute_number_of_files')

    _sql_constraints = [
        ('unique_name', 'UNIQUE (name)', 'Existing category name.'),
    ]

    def unlink(self):
        for record in self:
            if record.is_readonly:
                raise exceptions.UserError(
                    _('The read only categories cannot be removed.'))
        res = super().unlink()
        return res

    @api.depends('file_ids')
    def _compute_number_of_files(self):
        for record in self:
            if record.file_ids:
                record.number_of_files = len(record.file_ids)

    def action_get_files(self):
        self.ensure_one()
        if self.file_ids:
            id_tree_view = self.env.ref('crm_filemgmt.'
                                        'res_file_view_tree_related').id
            id_form_view = self.env.ref('crm_filemgmt.res_file_view_form').id
            search_view = self.env.ref('crm_filemgmt.res_file_view_search')
            act_window = {
                'type': 'ir.actions.act_window',
                'name': _('Files'),
                'res_model': 'res.file',
                'view_mode': 'tree',
                'views': [(id_tree_view, 'tree'),
                          (id_form_view, 'form')],
                'search_view_id': (search_view.id, search_view.name),
                'target': 'current',
                'domain': [('id', 'in', self.file_ids.ids)],
                }
            return act_window
