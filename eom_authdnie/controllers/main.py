# -*- coding: utf-8 -*-
# Copyright 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import http
from odoo.http import request
from odoo.addons.website.controllers.main import Website


class WebsiteEom(Website):

    def _get_name_parts(self, fullname):
        firstname = ''
        lastname = ''
        if fullname:
            if ',' in fullname:
                parts = fullname.split(',', 1)
                lastname = (parts[0] or '').strip()
                firstname = (parts[1] or '').strip()
            else:
                lastname = fullname.strip()
        return firstname, lastname

    def _format_identif_header(self, lastname, firstname, dni,
                               representative_lastname,
                               representative_firstname,
                               representative_dni):
        primary_name = lastname
        if firstname:
            primary_name = '%s, %s' % (lastname, firstname)
        header = '%s (%s)' % (primary_name, dni)
        if representative_dni:
            representative_name = representative_lastname
            if representative_firstname:
                representative_name = '%s, %s' % (
                    representative_lastname,
                    representative_firstname,
                )
            header = '%s - Representado por %s (%s)' % (
                header,
                representative_name,
                representative_dni,
            )
        return header

    @http.route('/eoffice', type='http', auth='public', website=True,
                csrf=False)
    def show_identification_data(self, **kwargs):
        country = ''
        dni = ''
        firstname = ''
        lastname = ''
        authority = ''
        represented_vat = ''
        representative_dni = ''
        representative_firstname = ''
        representative_lastname = ''
        identif_token = ''
        if request.httprequest.method == 'POST':
            identif_token = kwargs.get('identif_token', False)
            if identif_token:
                model_eom_authdnie = request.env['eom.digitalregister'].sudo()
                plain_text = model_eom_authdnie.decrypt_data(identif_token)
                if plain_text:
                    country, dni, firstname, lastname, authority, \
                        represented_name, represented_vat = \
                        model_eom_authdnie.get_items_of_decrypted_identif(
                            plain_text)
                    representative_dni = country + dni
                    representative_firstname = firstname
                    representative_lastname = lastname
                    if represented_vat:
                        dni = represented_vat
                        firstname = ''
                        lastname = represented_name or representative_lastname
        if country and dni and (firstname or lastname) and authority:
            if not represented_vat:
                dni = country + dni
            access = model_eom_authdnie.create_access(dni, firstname, lastname,
                                                      authority)
            return request.render(
                'eom_authdnie.identification_data_page',
                {'identif_token': identif_token,
                 'identif_header': self._format_identif_header(
                     lastname,
                     firstname,
                     dni,
                     representative_lastname,
                     representative_firstname,
                     representative_dni if represented_vat else '',
                 ),
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
        represented_vat = ''
        representative_firstname = ''
        representative_lastname = ''
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
                    country, dni, firstname, lastname, authority, \
                        represented_name, represented_vat = \
                        model_eom_authdnie.get_items_of_decrypted_identif(
                            plain_text)
                    representative_firstname = firstname
                    representative_lastname = lastname
                    if represented_vat:
                        dni = represented_vat
                        firstname = ''
                        lastname = represented_name or representative_lastname
                    access_name = kwargs.get('access_name', False)
                    summary = kwargs.get('summary', False)
                    detail = kwargs.get('detail', False)
        if (country and dni and (firstname or lastname) and authority and
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
