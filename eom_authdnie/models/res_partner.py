# -*- coding: utf-8 -*-
# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, exceptions, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    digitalregister_ids = fields.One2many(
        string='Possible digital register of the partner',
        comodel_name='eom.digitalregister',
        inverse_name='partner_id')

    digitalregister_id = fields.Many2one(
        string='Digital register of the partner',
        comodel_name='eom.digitalregister',
        store=True,
        compute='_compute_digitalregister_id',)

    digitalregisteraccess_ids = fields.One2many(
        string='Accesses of the partner',
        comodel_name='eom.digitalregister.access',
        inverse_name='partner_id')

    @api.depends('digitalregister_ids')
    def _compute_digitalregister_id(self):
        for record in self:
            digitalregister_id = None
            if (record.digitalregister_ids and
               len(record.digitalregister_ids) == 1):
                digitalregister_id = record.digitalregister_ids[0]
            record.digitalregister_id = digitalregister_id

    def _compute_user_in_group_eom_user(self):
        user_in_group_eom_user = \
            self.env.user.has_group(
                'eom_authdnie.user_in_group_eom_user')
        for record in self:
            record.user_in_group_eom_user = user_in_group_eom_user

    @api.constrains('digitalregister_ids')
    def _check_digitalregister_ids(self):
        for record in self:
            if (record.digitalregister_ids and
               len(record.digitalregister_ids) > 1):
                raise exceptions.ValidationError(_('A partner can only have '
                                                   'one digital register.'))

    @api.model_create_multi
    def create(self, vals):
        new_partner = super().create(vals)
        if 'vat' in vals and vals['vat']:
            new_partner.update_digitalregister()
        return new_partner

    def write(self, vals):
        resp = super().write(vals)
        if 'vat' in vals:
            self.update_digitalregister()
        return resp

    def update_digitalregister(self):
        for partner in self:
            if partner.vat:
                digitalregisters = self.env['eom.digitalregister'].search(
                    [('name', '=', partner.vat), ('partner_id', '=', False)])
                if digitalregisters and len(digitalregisters) == 1:
                    digitalregister = digitalregisters[0]
                    digitalregister.partner_id = partner
            else:
                digitalregisters = self.env['eom.digitalregister'].search(
                    [('partner_id', '=', partner.id)])
                if digitalregisters:
                    digitalregisters.write({'partner_id': None})

    def action_set_vat(self):
        self.ensure_one()
        user_in_group_eom_manager = self.env.user.has_group(
            'eom_authdnie.group_eom_manager')
        if user_in_group_eom_manager:
            act_window = {
                'type': 'ir.actions.act_window',
                'name': _('Contact') + ' : ' + self.name,
                'res_model': 'wizard.set.vat',
                'src_model': 'res.partner',
                'view_mode': 'form',
                'target': 'new',
                }
            return act_window
