# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _create_reconciliation_partials(self):
        '''Create the partial reconciliation between all the records in self.
         :return: A recordset of account.partial.reconcile.
        '''
        for line in self:
            if not line.date:
                line.date = line.move_id.date
        vals_list = [
            {
                'record': line,
                'balance': line.balance,
                'amount_currency': line.amount_currency,
                'amount_residual': line.amount_residual,
                'amount_residual_currency': line.amount_residual_currency,
                'company': line.company_id,
                'currency': line.currency_id,
                'date': line.date,
            }
            for line in self
        ]
        (partials_vals_list, exchange_data) = (
            self._prepare_reconciliation_partials(vals_list)
        )
        partials = self.env['account.partial.reconcile'].create(
            partials_vals_list
        )

        # ==== Create exchange difference moves ====
        for index, exchange_vals in exchange_data.items():
            partials[index].exchange_move_id = (
                self._create_exchange_difference_move(exchange_vals)
            )

        return partials
