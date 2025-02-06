# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.osv import expression



class FleetVehicleOdometer(models.Model):
    _inherit = 'fleet.vehicle.odometer'
    _description = 'Odometer log for a vehicle'
 
    initial_value = fields.Float(
        string='Initial Odometer Value',
        group_operator="max")
    project_id = fields.Many2one(
        comodel_name='project.project',
        string='Project',
        required=True)
    quantity = fields.Float(
        string='Quantity',
        compute='_compute_qty_odometer_kms')
    trip_driver_id = fields.Many2one(
        comodel_name='res.partner',
        string='Trip Driver',
        tracking=True,
        help='Driver of the trip',
        copy=False,
        default=lambda self: self._default_driver_id()
    )
    gap_exists_before = fields.Boolean(
        string='Gap Exists Before',
        compute='_compute_gap_exists_before',
        search='_search_gap_exists_before',
        default=False)

    @api.model
    def _default_driver_id(self):
        return self.vehicle_id.driver_id.id \
            if (self.vehicle_id and self.vehicle_id.driver_id) else False

    @api.depends('value', 'initial_value')
    def _compute_qty_odometer_kms(self):
        for record in self:
            record.quantity = record.value - record.initial_value
    #quiero un metodo compute _compute_gap_exists_before que mire todos los regidtros, y me diga si hay un gap entre el campo value del registro anterior al actual y el campo initial_value de este registro
    #si hay un gap, entonces el campo gap_exists_before de este registro debe ser True, si no hay gap, entonces el campo gap_exists_before de este registro debe ser False.
    #para esto, debo buscar el registro anterior al actual, y comparar el campo value de ese registro con el campo initial_value de este registro, pero se identifica como registro anterior por el valor que tiene el campo value


    def _compute_gap_exists_before(self):
        for record in self:
            previous_record = self.search([
                ('vehicle_id', '=', record.vehicle_id.id),
                ('initial_value', '<', record.initial_value)
            ], order='initial_value desc', limit=1)
            if previous_record:
                record.gap_exists_before = previous_record.value != record.initial_value
            else:
                record.gap_exists_before = False
            
    @api.onchange('trip_driver_id')
    def _onchange_trip_driver_id(self):
        for record in self:
            record.initial_value = record.vehicle_id.odometer
 
    @api.model
    def _search_gap_exists_before(self, operator, value):
        if operator not in ['=', '!=']:
            raise ValueError(f"Operador no soportado: {operator}")
        matching_ids = []
        all_records = self.search([])
        for record in all_records:
            prev_record = self.search([
                ('vehicle_id', '=', record.vehicle_id.id),
                ('initial_value', '<', record.initial_value)
            ], order='initial_value desc', limit=1)
            if prev_record and prev_record.value != record.initial_value:
                matching_ids.append(record.id)
            
            return [('id', 'in', matching_ids)] if operator == '=' else [
                ('id', 'not in', matching_ids)]

            
    
