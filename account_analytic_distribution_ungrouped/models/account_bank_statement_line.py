# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    analytic_account_single = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        compute='_compute_analytic_account_single',
        inverse='_inverse_analytic_account_single',
        store=False,
        help='Select an analytic account'
    )

    @api.depends('analytic_distribution')
    def _compute_analytic_account_single(self):
        for line in self:
            analytic_dist = getattr(line, 'analytic_distribution', None)
            if analytic_dist:
                # Take the first account from the JSON (we only handle one)
                account_ids = list(analytic_dist.keys())
                if account_ids:
                    try:
                        line.analytic_account_single = int(account_ids[0])
                    except (ValueError, TypeError):
                        line.analytic_account_single = False
                else:
                    line.analytic_account_single = False
            else:
                line.analytic_account_single = False

    def _inverse_analytic_account_single(self):
        for line in self:
            if hasattr(line, 'analytic_distribution'):
                if line.analytic_account_single:
                    # Assign 100% to the selected account
                    line.analytic_distribution = {
                        str(line.analytic_account_single.id): 100.0
                    }
                else:
                    line.analytic_distribution = {}
