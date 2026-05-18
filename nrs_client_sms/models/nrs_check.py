# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import phonenumbers
from phonenumbers import carrier
from phonenumbers.phonenumberutil import number_type
from odoo import models, fields, api, _


class NRSCheck(models.TransientModel):
    _name = "nrs.check"
    _description = "Check mobile numbers"

    partner_id = fields.Many2one(
        string='Partner',
        comodel_name='res.partner')

    phone_number = fields.Char(
        string="Phone number")

    phone_number_state = fields.Selection([
        ('ok', 'OK'),
        ('fail', 'FAIL'),
        ('not_set', 'NOT SET')],
        string="State")

    phone_number_state_description = fields.Char(
        string="State description")

    @api.model
    def run_check_mobile(self):
        self.env['nrs.check'].search([]).unlink()
        partners = self.env['res.partner'].search([])
        for partner in partners:
            partner_id = partner.id
            phone_number = ""
            phone_number_state = 'ok'
            phone_number_state_description = ""
            if not partner.mobile:
                phone_number = ""
                phone_number_state = 'not_set'
                phone_number_state_description = \
                    _("The mobile has not been set.")
            else:
                phone_number = partner.mobile.replace(" ", "").strip()
                if phone_number.startswith('+'):
                    phone_number = phone_number.strip('+')
                if not phone_number.isdigit():
                    phone_number = phone_number
                    phone_number_state = 'fail'
                    phone_number_state_description = \
                        _("Error there are characters that are not digits.")
                try:
                    reformated_phone_number = phonenumbers.format_number(
                        phonenumbers.parse(phone_number, "ES"),
                        phonenumbers.PhoneNumberFormat.E164)
                    phone_number = reformated_phone_number
                    phone_number_state_description = _("It seems correct.")
                except phonenumbers.NumberParseException as e:
                    phone_number = phone_number
                    phone_number_state = 'fail'
                    phone_number_state_description = str(e)
                try:
                    is_mobile = carrier._is_mobile(
                        number_type(phonenumbers.parse(phone_number, "ES")))
                    if not is_mobile:
                        phone_number = phone_number
                        phone_number_state = 'fail'
                        phone_number_state_description = \
                            _("Error does not have the correct format.")
                    else:
                        phone_number = phone_number
                        phone_number_state_description = _("It seems correct.")
                except phonenumbers.NumberParseException as e:
                    phone_number = phone_number
                    phone_number_state = 'fail'
                    phone_number_state_description = str(e)
                if phone_number.startswith('+'):
                    phone_number = phone_number.strip('+')
            mobile_data = {
                "partner_id": partner_id,
                "phone_number": phone_number,
                "phone_number_state": phone_number_state,
                "phone_number_state_description":
                    phone_number_state_description,
            }
            self.env['nrs.check'].create(mobile_data)
            self.env.cr.commit()
        id_tree_view = \
            self.env.ref('nrs_client_sms.nrs_check_view_tree').id
        search_view = \
            self.env.ref('nrs_client_sms.nrs_check_view_search')
        return {
            'name': _('NRS Mobile Check'),
            'view_type': 'form',
            'view_mode': 'tree',
            'views': [(id_tree_view, 'tree')],
            'search_view_id': (search_view.id, search_view.name),
            'res_model': 'nrs.check',
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
