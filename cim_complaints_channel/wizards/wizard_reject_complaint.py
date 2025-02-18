# -*- coding: utf-8 -*-
# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import models, fields, api


class WizardRejectComplaint(models.TransientModel):
    _name = 'wizard.reject.complaint'
    _description = 'Dialog box to reject a complaint'

    name = fields.Char(
        string='Code',)

    rejection_cause = fields.Text(
        string='Cause of the rejection',
        required=True,)

    @api.model
    def default_get(self, var_fields):
        resp = None
        record = self.env['cim.complaint'].browse(
            self.env.context['active_id'])
        if record:
            resp = {
                'name': record.name,
                }
        return resp

    def set_rejected(self):
        self.ensure_one()
        record = self.env['cim.complaint'].browse(
            self.env.context['active_id'])
        if record:
            record.write({
                'is_rejected': True,
                'rejection_cause': self.rejection_cause,
                })
            record._create_communication()
