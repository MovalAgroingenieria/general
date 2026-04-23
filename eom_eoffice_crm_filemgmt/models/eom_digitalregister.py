# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api
from odoo.exceptions import ValidationError


class EomDigitalregister(models.Model):
    _inherit = 'eom.digitalregister'

    @api.model
    def _get_vat_candidates(self, dni):
        vat_candidates = []
        vat = (dni or '').strip().upper()
        if not vat:
            return vat_candidates
        vat_candidates.append(vat)
        if len(vat) >= 2 and not vat[:2].isalpha():
            vat_candidates.append('ES' + vat)
        return list(dict.fromkeys(vat_candidates))

    # Overwrite parent method to create partner if it does not exist
    @api.model
    def create_access(self, dni, firstname, lastname, authority):
        if dni and (firstname or lastname) and authority:
            digitalregister = self.search([('name', '=', dni)])
            if not digitalregister:
                vals = {
                    'name': dni,
                    'firstname': firstname or '',
                    'lastname': lastname or '',
                    'authority': authority,
                    }
                digitalregister = self.create(vals)
            else:
                digitalregister = digitalregister[0]
                vals = {}
            model_digitalregister_access = \
                self.env['eom.digitalregister.access']
            new_access = model_digitalregister_access.create({
                'digitalregister_id': digitalregister.id, })
            model_res_partner = self.env['res.partner']
            vat_candidates = self._get_vat_candidates(dni)
            existing_partner = model_res_partner.search(
                [('vat', 'in', vat_candidates)], limit=1)
            if existing_partner:
                if not digitalregister.partner_id:
                    digitalregister.write({'partner_id': existing_partner.id})
            else:
                fullname = ((lastname or '') + ' ' +
                            (firstname or '')).strip()
                vals_partner = {
                    'name': fullname,
                    'is_company': not bool(firstname),
                    'created_by_authdnie': True,
                }
                partner_id = False
                for vat_candidate in vat_candidates:
                    vals_with_vat = dict(vals_partner, vat=vat_candidate)
                    try:
                        partner_id = model_res_partner.create(
                            vals_with_vat).id
                        break
                    except ValidationError:
                        pass
                if not partner_id:
                    partner_id = model_res_partner.create(vals_partner).id
                digitalregister.write({'partner_id': partner_id})
            return new_access
        else:
            return False
