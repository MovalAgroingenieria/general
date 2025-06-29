# -*- coding: utf-8 -*-
# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.http import request, route
from odoo.addons.portal.controllers.portal import CustomerPortal

CustomerPortal.OPTIONAL_BILLING_FIELDS.append('industry_id')
CustomerPortal.OPTIONAL_BILLING_FIELDS.append('websitepartner')
CustomerPortal.OPTIONAL_BILLING_FIELDS.append('category_id')
CustomerPortal.OPTIONAL_BILLING_FIELDS.append('categories_value_text')


class CustomCustomerPortal(CustomerPortal):

    @route()
    def account(self, redirect=None, **post):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        values.update({
            'error': {},
            'error_message': [],
        })
        if post and request.httprequest.method == 'POST':
            error, error_message = self.details_form_validate(post)
            values.update({'error': error, 'error_message': error_message})
            values.update(post)
            if not error:
                values = {key: post[key] for key in
                          self.MANDATORY_BILLING_FIELDS}
                values.update({key: post[key] for key in
                               self.OPTIONAL_BILLING_FIELDS if key in post})
                # Many2one
                for field in set(['country_id', 'state_id', 'industry_id']) & \
                        set(values.keys()):
                    try:
                        values[field] = int(values[field])
                    except Exception:
                        values[field] = False
                # Many2many
                for field in set(['categories_value_text']) & \
                        set(values.keys()):
                    try:
                        values[field] = [int(x) for x in
                                         values[field].split(',')]
                    except Exception:
                        values[field] = []
                values.update({'category_id':
                               [(6, 0, values['categories_value_text'])]})
                # Auxiliar values popped from values written
                values.pop('categories_value_text')
                # Rename fields
                values.update({'zip': values.pop('zipcode', '')})
                values.update({'website': values.pop('websitepartner', '')})
                partner.sudo().write(values)
                if redirect:
                    return request.redirect(redirect)
                return request.redirect('/my/home')

        countries = request.env['res.country'].sudo().search([])
        states = request.env['res.country.state'].sudo().search([])
        industries = request.env['res.partner.industry'].sudo().search([])
        categories = request.env['res.partner.category'].sudo().search([])
        partner_categories = ','.join(partner.category_id.mapped(
            lambda x: str(x.id)))
        values.update({
            'partner': partner,
            'countries': countries,
            'industries': industries,
            'categories': categories,
            'categories_text': partner_categories,
            'states': states,
            'has_check_vat': hasattr(request.env['res.partner'], 'check_vat'),
            'redirect': redirect,
            'page_name': 'my_details',
        })

        response = request.render("portal.portal_my_details", values)
        response.headers['X-Frame-Options'] = 'DENY'
        return response
