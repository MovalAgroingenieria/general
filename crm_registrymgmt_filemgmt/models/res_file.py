# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, _
from lxml import etree


class ResFile(models.Model):
    _inherit = 'res.file'

    registry_ids = fields.One2many(
        comodel_name='res.registry',
        inverse_name='file_id',
        string='Registries'
    )
    registry_count = fields.Integer(
        string='Registries count',
        compute='_compute_registry_count'
    )

    def _compute_registry_count(self):
        for record in self:
            record.registry_count = len(record.registry_ids)

    def action_get_registers(self):
        self.ensure_one()
        tree_view = \
            self.env.ref('crm_registrymgmt.res_registry_tree_view').id
        form_view = \
            self.env.ref('crm_registrymgmt.res_registry_form_view').id
        search_view = \
            self.env.ref('crm_registrymgmt.res_registry_search_view').id

        return {
            'type': 'ir.actions.act_window',
            'name': _('Registers'),
            'res_model': 'res.registry',
            'view_mode': 'tree,form',
            'views': [(tree_view, 'tree'), (form_view, 'form')],
            'search_view_id': search_view,
            'target': 'current',
            'domain': [('id', 'in', self.registry_ids.ids)],
        }

    def fields_view_get(self, view_id=None, view_type='form',
                        toolbar=False, submenu=False):
        res = super().fields_view_get(
            view_id=view_id,
            view_type=view_type,
            toolbar=toolbar,
            submenu=submenu,
        )

        if view_type == 'form':
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//button[@name='action_get_registers']"):
                node.set(
                    'modifiers',
                    '{"invisible": [["registry_count", "=", 0]]}'
                )
            res['arch'] = etree.tostring(doc, encoding='unicode')

        return res
