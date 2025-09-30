# -*- coding: utf-8 -*-
# Copyright 2019 Solvos Consultoría Informática (<http://www.solvos.es>)
# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    maintenance_request_id = fields.Many2one(
        comodel_name='maintenance.request',
        string='Maintenance Request',
    )

    maintenance_equipment_id = fields.Many2one(
        string='Maintenance Equipment',
        comodel_name='maintenance.equipment',
        compute='_compute_maintenance_equipment_id',
        store=True,
    )

    name = fields.Char(
        default='/',
    )

    @api.onchange('maintenance_request_id')
    def onchange_maintenance_request_id(self):
        if self.maintenance_request_id:
            self.name = self.maintenance_request_id.name
            if not self.project_id:
                self.project_id = self.maintenance_request_id.project_id
                self.task_id = self.maintenance_request_id.task_id

    @api.depends('maintenance_request_id',
                 'maintenance_request_id.equipment_id')
    def _compute_maintenance_equipment_id(self):
        for record in self:
            equipment_id = None
            if record.maintenance_request_id and \
                    record.maintenance_request_id.equipment_id:
                equipment_id = record.maintenance_request_id.equipment_id
            record.maintenance_equipment_id = equipment_id

    @api.model
    def create(self, values):
        if values.get('maintenance_request_id'):
            self._check_request_done(values.get('maintenance_request_id'))
        return super(AccountAnalyticLine, self).create(values)

    @api.multi
    def write(self, values):
        for timesheet in self:
            if timesheet.maintenance_request_id or values.get(
                    'maintenance_request_id', False):
                timesheet._check_request_done(
                    timesheet.maintenance_request_id.id
                    if timesheet.maintenance_request_id
                    else values['maintenance_request_id'])
        return super(AccountAnalyticLine, self).write(values)

    def unlink(self):
        for timesheet in self.filtered(lambda x: x.maintenance_request_id):
            self._check_request_done(timesheet.maintenance_request_id.id)
        super(AccountAnalyticLine, self).unlink()

    def _check_request_done(self, request_id):
        """
        Editing a timesheet related to a finished request is forbidden.
        """
        if self.env['maintenance.request'].browse(request_id).stage_id.done:
            raise ValidationError(_('Cannot save or delete a timesheet for '
                                    'a maintenance request already done'))
