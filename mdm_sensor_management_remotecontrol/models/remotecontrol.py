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

    def compute_device_multi_sensor_readings(self):
        self.ensure_one()
        computed_sensors = self.env[
            'mdm.measurement.device.sensor'].search([
                ('measurement_transformation_type', '=', 'multi_sensor'),
                ('device_id.remotecontrol_id', '=', self.id),
            ])
        result = computed_sensors.compute_multi_sensor_readings()
        return result


class RemoteControlAction(models.Model):
    _inherit = 'remotecontrol.action'

    def _prepare_action_context(self, bag=None):
        context = super(RemoteControlAction, self)._prepare_action_context(
            bag=bag)
        # Add selected_device_ids from bag if present (as list)
        context['selected_device_ids'] = bag.get('selected_device_ids', []) \
            if bag else []
        return context


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

    def _prepare_procedure_bag(self, bag=None):
        bag = super(RemoteControlProcedure, self)._prepare_procedure_bag(
            bag=bag)
        # Inject selected_device_ids from context into bag
        selected_device_ids = self.env.context.get('selected_device_ids', [])
        if selected_device_ids:
            bag['selected_device_ids'] = selected_device_ids
        return bag

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
