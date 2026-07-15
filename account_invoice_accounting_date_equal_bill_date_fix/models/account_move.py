# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends("invoice_date", "company_id")
    def _compute_date(self):
        result = super()._compute_date()
        supplier_moves = self.filtered(
            lambda move: move.move_type in ("in_invoice", "in_refund")
            and not move.date
        )
        for move in supplier_moves:
            move.date = fields.Date.context_today(move)
        return result
