# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api


class AccountModifyPaymentBatchesCommunication(models.Model):
    _name = "account.modify.payment.batches.communication"
    _description = "Account Modify Payment Batches Communication"
    _inherit = ["moval.external.app.screen.abstract"]

    APP_SLUG = "modificar-comunicacion-remesas"

    @api.model
    def _get_form_view_xmlid(self):
        xmlid = "account_modify_payment_batches_communication."\
            "account_modify_payment_batches_communication_home"
        return xmlid
