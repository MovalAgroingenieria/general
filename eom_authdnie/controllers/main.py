# -*- coding: utf-8 -*-
# Copyright 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import http
from odoo.http import request
from odoo.addons.website.controllers.main import Website


class WebsiteEom(Website):

    @http.route('/eoffice', type='http', auth='public', website=True,
                csrf=False)
    def show_identification_data(self, **kwargs):
        country = ''
        dni = ''
        firstname = ''
        lastname = ''
        authority = ''
        identif_token = ''
        if request.httprequest.method == 'POST':
            identif_token = kwargs.get('identif_token', False)
            if identif_token:
                model_eom_authdnie = request.env['eom.digitalregister'].sudo()
                plain_text = model_eom_authdnie.decrypt_data(identif_token)
                if plain_text:
                    country, dni, firstname, lastname, authority = \
                        model_eom_authdnie.get_items_of_decrypted_identif(
                            plain_text)
        if country and dni and firstname and lastname and authority:
            dni = country + dni
            access = model_eom_authdnie.create_access(dni, firstname, lastname,
                                                      authority)
            return request.render(
                'eom_authdnie.identification_data_page',
                {'identif_token': identif_token,
                 'identif_header': (lastname + ', ' + firstname +
                                    ' (' + dni + ')'),
                 'access': access, })
        else:
            return request.render(
                'eom_authdnie.identification_error', {})

    @http.route('/confirm', type='http', auth='public', website=True,
                csrf=False)
    def data_confirmation(self, **kwargs):
        country = ''
        dni = ''
        firstname = ''
        lastname = ''
        authority = ''
        identif_token = ''
        access_name = ''
        summary = ''
        detail = ''
        if request.httprequest.method == 'POST':
            identif_token = kwargs.get('identif_token', False)
            if identif_token:
                model_eom_authdnie = request.env['eom.digitalregister'].sudo()
                plain_text = model_eom_authdnie.decrypt_data(identif_token)
                if plain_text:
                    country, dni, firstname, lastname, authority = \
                        model_eom_authdnie.get_items_of_decrypted_identif(
                            plain_text)
                    access_name = kwargs.get('access_name', False)
                    summary = kwargs.get('summary', False)
                    detail = kwargs.get('detail', False)
        if (country and dni and firstname and lastname and authority and
           access_name and summary):
            model_eom_authdnie_access = \
                request.env['eom.digitalregister.access'].sudo()
            update_ok = model_eom_authdnie_access.update_access(
                access_name, summary, detail)
            return request.render(
                'eom_authdnie.confirmation_message', {
                    'update_ok': update_ok, })
        else:
            return request.render(
                'eom_authdnie.identification_error', {})
