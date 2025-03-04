# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from lxml import etree
from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    file_ids = fields.One2many(
        string='Associated Files',
        comodel_name='res.file.partnerlink',
        inverse_name='partner_id')

    number_of_files = fields.Integer(
        string='Num. of files',
        compute='_compute_number_of_files')

    def _compute_number_of_files(self):
        access_file_filemgmt = \
            self.env['res.file']._check_access_file_filemgmt()
        if access_file_filemgmt:
            for record in self:
                number_of_files = 0
                partnerlinks_of_partner = \
                    self.env['res.file.partnerlink'].search(
                        [('partner_id', '=', record.id)])
                if partnerlinks_of_partner:
                    number_of_files = len(partnerlinks_of_partner)
                record.number_of_files = number_of_files

    def action_get_files(self):
        self.ensure_one()
        if self.file_ids:
            id_tree_view = \
                self.env.ref('crm_filemgmt.'
                             'res_file_partnerlink_of_partner_view_tree').id
            search_view = \
                self.env.ref('crm_filemgmt.res_file_partnerlink_view_search')
            act_window = {
                'type': 'ir.actions.act_window',
                'name': _('File Partnerlinks'),
                'res_model': 'res.file.partnerlink',
                'view_mode': 'tree',
                'views': [(id_tree_view, 'tree')],
                'search_view_id': (search_view.id, search_view.name),
                'target': 'current',
                'domain': [('id', 'in', self.file_ids.ids)],
                }
            return act_window

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False,
                        submenu=False):
        res = super().fields_view_get(
            view_id=view_id,
            view_type=view_type,
            toolbar=toolbar,
            submenu=submenu,
        )
        access_file_filemgmt = \
            self.env['res.file']._check_access_file_filemgmt()
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            if not access_file_filemgmt:
                for node in doc.xpath(
                        "//button[@name='action_get_files']"):
                    node.set('modifiers', '{"invisible": true}')
            res['arch'] = etree.tostring(doc)
        return res
