# -*- coding: utf-8 -*-
# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import models, fields, api


class WizardComplainantData(models.TransientModel):
    _name = 'wizard.complainant.data'
    _description = 'Dialog box to enter the complainant data (encrypt/decrypt)'

    name = fields.Char(
        string='Code',)

    complainant_name = fields.Char(
        string='Complainant Name',)

    complainant_email = fields.Char(
        string='Complainant E-mail',)

    complainant_vat = fields.Char(
        string='Complainant VAT',)

    complainant_phone = fields.Char(
        string='Complainant Phone',)

    witness_name = fields.Text(
        string='Witnesses',)

    @api.model
    def default_get(self, var_fields):
        resp = None
        model_cim_complaint = self.env['cim.complaint']
        record = model_cim_complaint.browse(self.env.context['active_id'])
        if record:
            resp = {
                'name': record.name,
                'complainant_name': model_cim_complaint.decrypt_data(
                    record.complainant_name, model_cim_complaint._cipher_key),
                'complainant_email': model_cim_complaint.decrypt_data(
                    record.complainant_email, model_cim_complaint._cipher_key),
                'complainant_vat': model_cim_complaint.decrypt_data(
                    record.complainant_vat, model_cim_complaint._cipher_key),
                'complainant_phone': model_cim_complaint.decrypt_data(
                    record.complainant_phone, model_cim_complaint._cipher_key),
                'witness_name': model_cim_complaint.decrypt_data(
                    record.witness_name, model_cim_complaint._cipher_key),
            }
        return resp

    def set_complainant_data(self):
        self.ensure_one()
        model_cim_complaint = self.env['cim.complaint']
        record = model_cim_complaint.browse(self.env.context['active_id'])
        if record:
            record.write({
                'complainant_name': self.complainant_name,
                'complainant_email': self.complainant_email,
                'complainant_vat': self.complainant_vat,
                'complainant_phone': self.complainant_phone,
                'witness_name': self.witness_name,
            })
