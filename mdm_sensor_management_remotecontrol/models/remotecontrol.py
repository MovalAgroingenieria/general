# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _


class RemoteControl(models.Model):
    _inherit = 'remotecontrol'

    device_ids = fields.One2many(
        comodel_name='mdm.measurement.device',
        inverse_name='remotecontrol_id',
        string='Devices',
    )

    @api.multi
    def action_view_devices(self):
        self.ensure_one()
        if self.device_ids:
            id_tree_view = self.env.ref(
                'mdm_sensor_management.mdm_device_view_tree').id
            id_form_view = self.env.ref(
                'mdm_sensor_management.mdm_device_view_form').id
            search_view = self.env.ref(
                'mdm_sensor_management.mdm_device_view_search')
            act_window = {
                'type': 'ir.actions.act_window',
                'name': _('Devices'),
                'res_model': 'mdm.measurement.device',
                'view_type': 'form',
                'view_mode': 'tree',
                'views': [(id_tree_view, 'tree'), (id_form_view, 'form')],
                'search_view_id': (search_view.id, search_view.name),
                'target': 'current',
                'domain': [('id', 'in', self.device_ids.ids)],
                'context': {'default_remotecontrol_id': self.id},
            }
            return act_window
