# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, exceptions, _


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


class RemoteControlProcedure(models.Model):
    _inherit = 'remotecontrol.procedure'

    def _get_procedure_for_readings(self):
        resp = False
        remote_id = self.env.context.get('default_remote_id', False)
        if remote_id:
            existing_procedures_for_readings = self.search(
                [('remote_id', '=', remote_id),
                 ('procedure_for_readings', '=', True)])
            if not existing_procedures_for_readings:
                resp = True
        return resp

    procedure_for_readings = fields.Boolean(
        string='Procedure for readings (y/n)',
        required=True,
        default=_get_procedure_for_readings,
    )

    @api.constrains('procedure_for_readings')
    def _check_procedure_for_readings(self):
        for record in self:
            if record.procedure_for_readings:
                existing_procedures_for_readings = self.search(
                    [('remote_id', '=', record.remote_id.id),
                     ('procedure_for_readings', '=', True)])
                if (existing_procedures_for_readings and
                   len(existing_procedures_for_readings) > 1):
                    raise exceptions.ValidationError(
                        _('There is already a procedure that has been marked '
                          'as \'Procedure for readings\'.'))
