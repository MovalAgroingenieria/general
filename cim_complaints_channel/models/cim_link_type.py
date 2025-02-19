# -*- coding: utf-8 -*-
# Copyright 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, exceptions, _


class CimLinkType(models.Model):
    _name = 'cim.link.type'
    _description = 'Link Type'
    _order = 'name'

    SIZE_NAME = 75

    name = fields.Char(
        string='Name',
        size=SIZE_NAME,
        required=True,
        index=True,
        translate=True,)

    is_standard = fields.Boolean(
        string='Standard Type (y/n)',
        default=False)

    complaint_ids = fields.One2many(
        string='Complaints',
        comodel_name='cim.complaint',
        inverse_name='link_type_id',)

    number_of_complaints = fields.Integer(
        string='Number of complaints',
        compute='_compute_number_of_complaints',)

    notes = fields.Html(
        string='Notes',)

    notes_text = fields.Char(
        string='Notes (as text)',
        compute='_compute_notes_text',)

    active = fields.Boolean(
        default=True,)

    def _compute_number_of_complaints(self):
        for record in self:
            number_of_complaints = 0
            if record.complaint_ids:
                number_of_complaints = len(record.complaint_ids)
            record.number_of_complaints = number_of_complaints

    def _compute_notes_text(self):
        model_converter = self.env['ir.fields.converter']
        for record in self:
            notes_text = ''
            if record.notes:
                notes_text = model_converter.text_from_html(
                    record.notes, 50, 150)
            record.notes_text = notes_text

    def unlink(self):
        for record in self:
            if record.is_standard:
                raise exceptions.UserError(_('It is not possible to remove '
                                             'a \'STANDARD\' link type.'))
        res = super(CimLinkType, self).unlink()
        return res

    def action_show_complaints(self):
        self.ensure_one()
        current_link_type = self
        id_tree_view = self.env.ref(
            'cim_complaints_channel.cim_complaint_view_tree').id
        id_form_view = self.env.ref(
            'cim_complaints_channel.cim_complaint_view_form').id
        search_view = self.env.ref(
            'cim_complaints_channel.cim_complaint_view_search')
        custom_context = \
            {'default_link_type_id': current_link_type.id}
        act_window = {
            'type': 'ir.actions.act_window',
            'name': _('Complaints'),
            'res_model': 'cim.complaint',
            'view_type': 'form',
            'view_mode': 'form,tree',
            'views': [(id_tree_view, 'tree'), (id_form_view, 'form')],
            'search_view_id': [search_view.id],
            'target': 'current',
            'domain': [('link_type_id', '=', current_link_type.id)],
            'context': custom_context,
            }
        return act_window
