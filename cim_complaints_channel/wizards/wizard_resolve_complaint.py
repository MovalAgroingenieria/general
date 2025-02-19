# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import models, fields, api


class WizardResolveComplaint(models.TransientModel):
    _name = 'wizard.resolve.complaint'
    _description = 'Dialog box to resolve a complaint'

    name = fields.Char(
        string='Code',)

    resolution_text = fields.Text(
        string='Resolution Text',
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

    def set_state_to_05_resolved(self):
        self.ensure_one()
        record = self.env['cim.complaint'].browse(
            self.env.context['active_id'])
        if record:
            record.write({
                'state': '05_resolved',
                'resolution_text': self.resolution_text,
                })
            if record.automatic_email_state:
                record._create_communication()
