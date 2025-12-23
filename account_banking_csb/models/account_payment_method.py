# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models


class AccountPaymentMethod(models.Model):
    _inherit = "account.payment.method"

    def write(self, vals):
        res = super().write(vals)
        trigger_fields = {"active", "payment_order_only", "payment_type", "code"}
        if trigger_fields.intersection(vals.keys()):
            # Invalida el cache del compute en journals afectados
            journals = self.env["account.journal"].search(
                [("type", "in", ("bank", "cash", "credit"))]
            )
            journals.invalidate_recordset(["available_payment_method_ids"])
        return res
