# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountBankStatement(models.Model):
    _inherit = "account.bank.statement"

    # TO be checked by later callbacks
    bankinplay_signature = fields.Char(
        string="Bankinplay signature",
        readonly=True,
        copy=False,
    )

    bankinplay_responseid = fields.Char(
        string="Bankinplay response id",
        readonly=True,
        copy=False,
    )

    bankinplay_date_since = fields.Datetime(
        string="Bankinplay date since id",
        readonly=True,
        copy=False,
    )

    bankinplay_date_until = fields.Datetime(
        string="Bankinplay date until",
        readonly=True,
        copy=False,
    )
