# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _


class MeasurementDeviceCategory(models.Model):
    _name = 'mdm.measurement.device.category'
    _description = 'Measurement Device Category'
    _order = 'name'

    name = fields.Char(
        string='Name',
        required=True,
        index=True,
    )

    description = fields.Text(
        string='Description',
    )

    device_ids = fields.One2many(
        comodel_name='mdm.measurement.device',
        inverse_name='category_id',
        string='Devices',
    )

    device_count = fields.Integer(
        string='Device Count',
        compute='_compute_device_count',
    )

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'Category name must be unique!'),
    ]

    @api.depends('device_ids')
    def _compute_device_count(self):
        for category in self:
            device_count = 0
            if category.device_ids:
                device_count = len(category.device_ids)
            category.device_count = device_count

    @api.multi
    def action_view_devices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Devices'),
            'res_model': 'mdm.measurement.device',
            'view_mode': 'tree,form',
            'domain': [('category_id', '=', self.id)],
            'context': {'default_category_id': self.id},
        }
