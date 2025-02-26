# -*- coding: utf-8 -*-
# Copyright 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, _


class EomDigitalregister(models.Model):
    _inherit = 'eom.digitalregister'

    notification_address = fields.Char(
        string='Notification Address')

    notification_phone = fields.Char(
        string='Notification Phone')

    notification_mobile = fields.Char(
        string='Notification Mobile')

    notification_email = fields.Char(
        string='Notification Email')

    postal_notification = fields.Boolean(
        string='Postal Notification')

    file_ids = fields.One2many(
        string='Electronic files of the certificate',
        comodel_name='eom.electronicfile',
        inverse_name='digitalregister_id')

    number_of_files = fields.Integer(
        string='Number of electronic files',
        compute='_compute_number_of_files',)

    @api.depends('file_ids')
    def _compute_number_of_files(self):
        for record in self:
            record.number_of_files = len(record.file_ids)

    def action_electronic_files(self):
        self.ensure_one()
        current_digitalregister = self
        id_kanban_view = self.env.ref(
            'eom_eoffice.eom_electronicfile_view_kanban').id
        id_tree_view = self.env.ref(
            'eom_eoffice.eom_electronicfile_view_tree').id
        id_form_view = self.env.ref(
            'eom_eoffice.eom_electronicfile_view_form').id
        search_view = self.env.ref(
            'eom_eoffice.eom_electronicfile_view_search')
        act_window = {
            'type': 'ir.actions.act_window',
            'name': _('Files'),
            'res_model': 'eom.electronicfile',
            'view_mode': 'kanban,form,tree',
            'views': [(id_kanban_view, 'kanban'), (id_tree_view, 'tree'),
                      (id_form_view, 'form')],
            'search_view_id': [search_view.id],
            'target': 'current',
            'domain': [('digitalregister_id', '=',
                        current_digitalregister.id)],
            'context': {'hide_image': True,
                        'search_default_grouped_event_time': True,
                        'reduced_register_id': True,
                        'reduced_access_id': True},
            }
        return act_window

    @api.model_create_multi
    def create(self, vals):
        if 'partner_id' in vals:
            partner = self.env['res.partner'].browse(vals['partner_id'])
            # Address
            address_data = ""
            if partner.street:
                address_data += partner.street
            if partner.street2:
                address_data += ' ' + partner.street2
            address_data += '. '
            if partner.zip:
                address_data += partner.zip
            address_data += ' - '
            if partner.city:
                address_data += partner.city
            if partner.state_id:
                state = partner.state_id.name + ', '
            else:
                state = ''
            if partner.country_id:
                country = partner.country_id.name
            address_data += ' (' + state + country + ')'
            vals['notification_address'] = address_data
            # Phone
            if partner.phone:
                vals['notification_phone'] = partner.phone
            # Mobile
            if partner.mobile:
                vals['notification_mobile'] = partner.mobile
            # Email
            if partner.email:
                vals['notification_email'] = partner.email
                vals['postal_notification'] = False
            else:
                vals['postal_notification'] = True
        return super().create(vals)
