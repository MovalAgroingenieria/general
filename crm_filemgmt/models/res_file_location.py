# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, _


class ResFileLocation(models.Model):
    _name = 'res.file.location'
    _description = "Locations of Files"

    name = fields.Char(
        string='Name',
        required=True,
        index=True)

    description = fields.Char(
        string='Description',)

    location_id = fields.Many2one(
        string='Site',
        comodel_name='res.file.location',
        ondelete='restrict',)

    image = fields.Binary(
        string='Photo / Image',
        attachment=True,)

    container_ids = fields.One2many(
        string='Containers',
        comodel_name='res.file.container',
        inverse_name='location_id',)

    notes = fields.Html(
        string='Notes',)

    number_of_containers = fields.Integer(
        string='Files',
        store=True,
        compute='_compute_number_of_containers',)

    _sql_constraints = [
        ('unique_name', 'UNIQUE (name)', 'Existing location name.')]

    @api.depends('container_ids')
    def _compute_number_of_containers(self):
        for record in self:
            if record.container_ids:
                record.number_of_containers = len(record.container_ids)

    def action_get_containers(self):
        self.ensure_one()
        if self.container_ids:
            id_tree_view = self.env.ref(
                'crm_filemgmt.res_file_container_view_tree_related').id
            id_form_view = self.env.ref(
                'crm_filemgmt.res_file_container_view_form').id
            search_view = self.env.ref(
                'crm_filemgmt.res_file_container_view_search')
            act_window = {
                'type': 'ir.actions.act_window',
                'name': _('Containers'),
                'res_model': 'res.file.container',
                'view_mode': 'tree',
                'views': [(id_tree_view, 'tree'),
                          (id_form_view, 'form')],
                'search_view_id': (search_view.id, search_view.name),
                'target': 'current',
                'domain': [('id', 'in', self.container_ids.ids)],
                }
            return act_window
