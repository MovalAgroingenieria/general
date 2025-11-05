# -*- coding: utf-8 -*-
# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    computed_customer_payment_mode_id = fields.Many2one(
        comodel_name="account.payment.mode",
        store=True,
        compute="_compute_computed_customer_payment_mode_id",)

    @api.depends('customer_payment_mode_id')
    def _compute_computed_customer_payment_mode_id(self):
        for record in self:
            if record.customer_payment_mode_id:
                record.computed_customer_payment_mode_id = \
                    record.customer_payment_mode_id
