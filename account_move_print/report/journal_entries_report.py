# -*- coding: utf-8 -*-
# Copyright 2017-20 ForgeFlow S.L. (https://www.forgeflow.com)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from odoo import api, models
from odoo.tools.misc import formatLang


class JournalEntriesReport(models.AbstractModel):
    _name = 'report.account_move_print.journal_entries_report_id'

    @api.multi
    def render_html(self, docids, data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name(
            'account_move_print.journal_entries_report_id'
        )
        moves = self.env['account.move'].browse(docids)
        moves_data = self._get_moves_data(moves)
        docargs = {
            'doc_ids': docids,
            'doc_model': report.model,
            'docs': moves,
            'moves_data': moves_data,
        }
        return report_obj.render(
            'account_move_print.journal_entries_report_id', docargs
        )

    @api.multi
    def _get_moves_data(self, moves):
        """Pre-fetch all data in bulk to avoid N+1 queries in QWeb."""
        res = {}
        if not moves:
            return res

        # Single SQL query to fetch all line data with JOINs
        self.env.cr.execute("""
            SELECT
                aml.move_id,
                aml.id AS line_id,
                aa.code || ' ' || aa.name AS account_name,
                rp.name AS partner_name,
                aml.name AS line_name,
                aaa.name AS analytic_name,
                aml.amount_currency,
                cur.name AS currency_name,
                cur.symbol AS currency_symbol,
                aml.debit,
                aml.credit,
                atax.name AS tax_line_name,
                COALESCE(
                    (SELECT string_agg(at2.name, ', ')
                     FROM account_move_line_account_tax_rel rel
                     JOIN account_tax at2 ON at2.id = rel.account_tax_id
                     WHERE rel.account_move_line_id = aml.id),
                    ''
                ) AS tax_names
            FROM account_move_line aml
            JOIN account_account aa ON aa.id = aml.account_id
            LEFT JOIN res_partner rp ON rp.id = aml.partner_id
            LEFT JOIN account_analytic_account aaa
                ON aaa.id = aml.analytic_account_id
            LEFT JOIN res_currency cur ON cur.id = aml.currency_id
            LEFT JOIN account_tax atax ON atax.id = aml.tax_line_id
            WHERE aml.move_id IN %s
            ORDER BY aml.move_id, aml.id
        """, (tuple(moves.ids),))

        rows = self.env.cr.dictfetchall()

        # Get company currency info
        company_currency = moves[0].company_id.currency_id

        for move in moves:
            move_lines = []
            total_debit = 0.0
            total_credit = 0.0
            for row in rows:
                if row['move_id'] == move.id:
                    total_debit += row['debit']
                    total_credit += row['credit']
                    # Format monetary values using Odoo's formatLang
                    row['debit_fmt'] = formatLang(
                        self.env, row['debit'],
                        currency_obj=company_currency,
                    )
                    row['credit_fmt'] = formatLang(
                        self.env, row['credit'],
                        currency_obj=company_currency,
                    )
                    if row['amount_currency'] and row['currency_symbol']:
                        amt_currency = self.env['res.currency'].search(
                            [('name', '=', row['currency_name'])], limit=1
                        )
                        row['amount_currency_fmt'] = formatLang(
                            self.env, row['amount_currency'],
                            currency_obj=amt_currency,
                        ) if amt_currency else ''
                    else:
                        row['amount_currency_fmt'] = ''
                    move_lines.append(row)

            res[move.id] = {
                'lines': move_lines,
                'total_debit': total_debit,
                'total_credit': total_credit,
                'total_debit_fmt': formatLang(
                    self.env, total_debit,
                    currency_obj=company_currency,
                ),
                'total_credit_fmt': formatLang(
                    self.env, total_credit,
                    currency_obj=company_currency,
                ),
            }
        return res
