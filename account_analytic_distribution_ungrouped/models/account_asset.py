# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    # Many2one field for a single analytic account
    # (account.asset inherits analytic.mixin which has analytic_distribution)
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
        for asset in self:
            if asset.analytic_distribution:
                # Take the first account from the JSON (we only handle one)
                account_ids = list(asset.analytic_distribution.keys())
                if account_ids:
                    asset.analytic_account_single = int(account_ids[0])
                else:
                    asset.analytic_account_single = False
            else:
                asset.analytic_account_single = False

    def _inverse_analytic_account_single(self):
        for asset in self:
            if asset.analytic_account_single:
                # Assign 100% to the selected account
                asset.analytic_distribution = {
                    str(asset.analytic_account_single.id): 100.0
                }
            else:
                asset.analytic_distribution = {}
