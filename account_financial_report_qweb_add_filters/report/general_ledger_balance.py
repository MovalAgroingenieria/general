# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ReportGeneralLedgerBalanceGrouped(models.TransientModel):

    _name = "report_general_ledger_balance_grouped"

    # Filters fields, used for data computation
    date_from = fields.Date()
    date_to = fields.Date()
    fy_start_date = fields.Date()
    company_id = fields.Many2one(comodel_name="res.company")
    account_ids = fields.One2many(
        comodel_name="report_trial_balance_qweb_account",
        inverse_name="report_id",
    )
    initial_balance = fields.Float(digits=(16, 2))
    initial_balance_foreign_currency = fields.Float(digits=(16, 2))
    debit = fields.Float(digits=(16, 2))
    credit = fields.Float(digits=(16, 2))
    balance = fields.Float(digits=(16, 2))
    currency_id = fields.Many2one(comodel_name="res.currency")
    final_balance = fields.Float(digits=(16, 2))
    final_balance_foreign_currency = fields.Float(digits=(16, 2))
    partner_ids = fields.One2many(
        comodel_name="report_trial_balance_qweb_partner",
        inverse_name="report_account_id",
    )
