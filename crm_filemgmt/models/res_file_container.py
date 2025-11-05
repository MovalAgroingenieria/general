# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, _


class ResFileContainer(models.Model):
    _name = 'res.file.container'
    _description = "Container of Files"

    name = fields.Char(
        string='Name',
        required=True,)

    description = fields.Char(
        string='Description',
        required=True,
        index=True,)

    location_id = fields.Many2one(
        string='Location',
        comodel_name='res.file.location',
        required=True,
        index=True,
        ondelete='restrict',)

    image = fields.Image(
        string='Photo / Image',)

    file_ids = fields.One2many(
        string='Files',
        comodel_name='res.file',
        inverse_name='container_id',)

    number_of_files = fields.Integer(
        string='Number of Files',
        store=True,
        compute='_compute_number_of_files',)

    containertype_id = fields.Many2one(
        string='Type',
        comodel_name='res.file.containertype',
        index=True,
        ondelete='restrict',)

    notes = fields.Html(
        string='Notes')

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
                'view_type': 'form',
                'view_mode': 'tree',
                'views': [(id_tree_view, 'tree'),
                          (id_form_view, 'form')],
                'search_view_id': (search_view.id, search_view.name),
                'target': 'current',
                'domain': [('id', 'in', self.file_ids.ids)],
                }
            return act_window

    def name_get(self):
        resp = []
        for record in self:
            name = record.description + \
                ' [' + str(record.name) + ']'
            if self.env.context.get('show_container_data', False):
                name += _(' [location: ') + \
                    record.location_id.description + ']'
                if record.containertype_id:
                    name += _(' [type: ') + \
                        record.containertype_id.name + ']'
            resp.append((record.id, name))
        return resp
