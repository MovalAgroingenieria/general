# -*- coding: utf-8 -*-
# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import models, fields, api


class WizardSetVat(models.TransientModel):
    _name = 'wizard.set.vat'
    _description = 'Dialog box to set a VAT'

    vat = fields.Char(
        string='VAT',)

    @api.model
    def default_get(self, var_fields):
        resp = None
        record = self.env['res.partner'].browse(
            self.env.context['active_id'])
        if record:
            resp = {
                'vat': record.vat,
                }
        return resp

    def set_vat(self):
        self.ensure_one()
        record = self.env['res.partner'].browse(
            self.env.context['active_id'])
        if record:
            vat = self.vat
            if not vat:
                vat = None
            else:
                vat = vat.strip().upper()
                if vat[0].isdigit():
                    vat = 'ES' + vat
            record.write({
                'vat': vat,
                })
