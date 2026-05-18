# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends("invoice_date", "company_id")
    def _compute_date(self):
        if self.env.context.get("create_bill") or self.env.context.get(
            "auditlog_disabled"
        ):
            return super()._compute_date()
        supplier_moves = self.filtered(
            lambda m: m.move_type in ("in_invoice", "in_refund")
        )
        for move in supplier_moves:
            move.date = move.invoice_date or fields.Date.context_today(self)
        other_moves = self - supplier_moves
        if other_moves:
            super(AccountMove, other_moves)._compute_date()
