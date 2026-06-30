# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError


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

    readonly = fields.Boolean(
        string='Read Only',
        readonly=True,
        default=False,
        help='Indicates if this category was created by module '
             'installation and should not be deleted',
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

    @api.model
    def create(self, vals):
        if self.env.context.get('install_mode') and vals.get('name'):
            existing = self.with_context(active_test=False).search(
                [('name', '=', vals['name'])],
                limit=1,
            )
            if existing:
                return existing
        return super(MeasurementDeviceCategory, self).create(vals)

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

    @api.multi
    def unlink(self):
        allow_unlink = (
            self.env.context.get('force_unlink', False) or
            self.env.context.get('uninstall_mode', False) or
            self.env.context.get('module_uninstall', False)
        )
        if not allow_unlink:
            for record in self:
                if record.readonly:
                    raise UserError(
                        _('You cannot delete a read-only category.'),
                    )
        return super(MeasurementDeviceCategory, self).unlink()
