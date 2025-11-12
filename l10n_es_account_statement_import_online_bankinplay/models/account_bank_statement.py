# 2024-2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountBankStatement(models.Model):
    _inherit = "account.bank.statement"

    # --- BankInPlay callback correlation fields -----------------------------
    bankinplay_signature = fields.Char(
        help="Signature returned by Bankinplay to authenticate the callback.",
        readonly=True,
        copy=False,
        index=True,
    )

    bankinplay_responseid = fields.Char(
        help="Response identifier returned by Bankinplay for this request.",
        readonly=True,
        copy=False,
        index=True,
    )

    # --- Requested window used to build this statement ----------------------
    bankinplay_date_since = fields.Datetime(
        help="Start datetime used when requesting close movements.",
        readonly=True,
        copy=False,
    )

    bankinplay_date_until = fields.Datetime(
        help="End datetime used when requesting close movements.",
        readonly=True,
        copy=False,
    )

    _sql_constraints = [
        # Prevent creating two statements for the same Bankinplay callback
        (
            "bankinplay_resp_sig_unique",
            "unique(bankinplay_responseid, bankinplay_signature)",
            "A statement for this Bankinplay response/signature already exists.",
        ),
    ]
