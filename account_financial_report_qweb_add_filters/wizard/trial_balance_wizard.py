# -*- coding: utf-8 -*-
# Author: Julien Coux
# Copyright 2016 Camptocamp SA
# Copyright 2017 Akretion - Alexis de Lattre
# Copyright 2018 Eficent Business and IT Consuting Services, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


class TrialBalanceReportWizard(models.TransientModel):
    """Trial balance report wizard."""

    _name = "trial.balance.report.grouped.wizard"
    _description = "Trial Balance Report Wizard"

    company_id = fields.Many2one(
        comodel_name='res.company',
        default=lambda self: self.env.user.company_id,
        required=False,
        string='Company',
    )
    date_range_id = fields.Many2one(
        comodel_name='date.range',
        string='Date range',
    )
    partner_ids = fields.Many2many(
        comodel_name='res.partner',
        string='Filter partners',
    )
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    fy_start_date = fields.Date(compute='_compute_fy_start_date')

    account_ids = fields.Many2many(
        comodel_name='account.account',
        string='Filter accounts',
    )
    journal_ids = fields.Many2many(
        comodel_name="account.journal",
        string="Filter journals",
    )
    show_account_zero = fields.Boolean(
        string='Show account at 0',
    )

    @api.onchange('company_id')
    def onchange_company_id(self):
        """Handle company change."""
        account_type = self.env.ref('account.data_unaffected_earnings')
        count = self.env['account.account'].search_count(
            [
                ('user_type_id', '=', account_type.id),
                ('company_id', '=', self.company_id.id),
            ])
        self.not_only_one_unaffected_earnings_account = count != 1
        if self.company_id and self.date_range_id.company_id and \
                self.date_range_id.company_id != self.company_id:
            self.date_range_id = False
        if self.company_id and self.partner_ids:
            self.partner_ids = self.partner_ids.filtered(
                lambda p: p.company_id == self.company_id or
                not p.company_id)
        if self.company_id and self.journal_ids:
            self.journal_ids = self.journal_ids.filtered(
                lambda a: a.company_id == self.company_id)
        if self.company_id and self.account_ids:
            if self.receivable_accounts_only or self.payable_accounts_only:
                self.onchange_type_accounts_only()
            else:
                self.account_ids = self.account_ids.filtered(
                    lambda a: a.company_id == self.company_id)
        res = {'domain': {'account_ids': [],
                          'partner_ids': [],
                          'date_range_id': [],
                          'journal_ids': [],
                          },
               }
        if not self.company_id:
            return res
        else:
            res['domain']['account_ids'] += [
                ('company_id', '=', self.company_id.id)]
            res['domain']['partner_ids'] += [
                '&',
                '|', ('company_id', '=', self.company_id.id),
                ('company_id', '=', False),
                ('parent_id', '=', False)]
            res['domain']['date_range_id'] += [
                '|', ('company_id', '=', self.company_id.id),
                ('company_id', '=', False)]
            res['domain']['journal_ids'] += [
                ('company_id', '=', self.company_id.id)]
        return res

    @api.depends('date_from')
    def _compute_fy_start_date(self):
        for wiz in self.filtered('date_from'):
            date = fields.Datetime.from_string(wiz.date_from)
            res = self.company_id.compute_fiscalyear_dates(date)
            wiz.fy_start_date = res['date_from']

    @api.onchange('date_range_id')
    def onchange_date_range_id(self):
        """Handle date range change."""
        self.date_from = self.date_range_id.date_start
        self.date_to = self.date_range_id.date_end

    @api.multi
    @api.constrains('company_id', 'date_range_id')
    def _check_company_id_date_range_id(self):
        for rec in self.sudo():
            if rec.company_id and rec.date_range_id.company_id and\
                    rec.company_id != rec.date_range_id.company_id:
                raise ValidationError(
                    _('The Company in the Trial Balance Report Wizard and in '
                      'Date Range must be the same.'))

    @api.multi
    def get_accounts(self):
        """Retrieve accounts based on the selected filters."""
        domain = [('company_id', '=', self.company_id.id)]
        if self.account_ids:
            domain.append(('id', 'in', self.account_ids.ids))
        accounts = self.env['account.account'].search(domain)
        if not accounts:
            return []
        return accounts

    def get_group_by_field(self, account):
        """Determine the field to group by based on account type."""
        if account.user_type_id.group_by == 'product_id':
            return 'product_id'
        elif account.user_type_id.group_by == 'partner_id':
            return 'partner_id'
        elif account.user_type_id.group_by == 'journal_id':
            return 'journal_id'
        elif account.user_type_id.group_by == 'tag':
            return 'name'
        elif account.user_type_id.group_by == 'analytic_account_id':
            return 'analytic_account_id'
        return None

    @api.multi
    def get_item_ids(self, account, start_date, end_date):
        group_by_field = self.get_group_by_field(account)

        # Construir el dominio de búsqueda
        domain = [
            ('account_id', '=', account.id),
            ('date', '>=', start_date),
            ('date', '<=', end_date),
        ]
        # domain_back: move lines before the period, used to discover
        # group values (partners, products…) that carry an initial balance.
        # No reconciliation filter here — a trial balance reports all
        # entries regardless of their reconciliation status.
        domain_back = [
            ('account_id', '=', account.id),
            ('date', '<=', start_date),
        ]
        if group_by_field:
            # Usar read_group si se especifica un campo de agrupación
            move_lines = self.env['account.move.line'].read_group(
                domain=domain,
                fields=['credit:sum', 'debit:sum', 'balance:sum',
                        group_by_field],
                groupby=[group_by_field],
            )
            move_lines_back = self.env['account.move.line'].read_group(
                domain=domain_back,
                fields=['credit:sum', 'debit:sum', 'balance:sum',
                        group_by_field],
                groupby=[group_by_field],
            )
            item_lines = []
            # all_mlines = move_lines + move_lines_back
            # all_mlines_dict = {line[group_by_field]: line for line in
            #                    move_lines + move_lines_back}

            # Convertir el diccionario de vuelta a una lista de diccionarios
            # all_mlines = list(all_mlines_dict.values())
            # if (group_by_field == 'partner_id'):
            #     partners_in_move_lines = {line['partner_id']: line for line
            #       in
            #                           move_lines}
            # Diccionario dinámico en función del campo de agrupación
            values_in_move_lines = {line[group_by_field]: line for line in
                                    move_lines}

            # Recorremos cada elemento en move_lines_back
            # move_lines_old = []
            for line in move_lines_back:
                # Obtenemos el valor de agrupación actual
                group_value = line.get(group_by_field)

                # Si el partner_id no está en move_lines, añadimos el registro
                if (values_in_move_lines and
                        group_value not in values_in_move_lines or
                        not values_in_move_lines):

                    initial_balance = self.get_initial_balance(
                        account, group_value, start_date)
                    line['credit'] = 0
                    line['debit'] = 0
                    line['balance'] = 0
                    final_balance = initial_balance + line['balance']
                    # Verificamos si la cuenta es cero para excluir si es
                    # necesario
                    if (not self.show_account_zero and not initial_balance and
                            line.get('credit') == 0 and line.get('debit') ==
                            0):
                        continue
                    else:
                        item_lines.append({
                            'credit': line.get('credit', 0.0),
                            'debit': line.get('debit', 0.0),
                            'balance': line.get('balance', 0.0),
                            'initial_balance': initial_balance,
                            'final_balance': final_balance,
                            'product_id': line.get('product_id', False),
                            'partner_id': line.get('partner_id', False),
                            'journal_id': line.get('journal_id', False),
                            'tag': line.get('name', False),
                            'analytic_account_id': line.get(
                                'analytic_account_id', False),
                        })
            for line in move_lines:
                group_value = line.get(group_by_field)
                initial_balance = self.get_initial_balance(
                    account, group_value, start_date)
                final_balance = initial_balance + line['balance']
                if (not self.show_account_zero and not initial_balance and
                        line.get('credit') == 0 and line.get('debit') == 0):
                    continue
                else:
                    item_lines.append({
                        'credit': line.get('credit', 0.0),
                        'debit': line.get('debit', 0.0),
                        'balance': line.get('balance', 0.0),
                        'initial_balance': initial_balance,
                        'final_balance': final_balance,
                        'product_id': line.get('product_id', False),
                        'partner_id': line.get('partner_id', False),
                        'journal_id': line.get('journal_id', False),
                        'tag': line.get('name', False),
                        'analytic_account_id': line.get(
                            'analytic_account_id', False),
                    })
        else:
            # Devolver líneas individuales si no hay campo de agrupación
            move_lines = self.env['account.move.line'].search(domain,
                                                              order='id')
            item_lines = []
            initial_balance = self.get_initial_balance(account, None,
                                                       start_date)
            total_debit = sum(line.debit for line in move_lines)
            total_credit = sum(line.credit for line in move_lines)
            final_balance = initial_balance + (total_debit - total_credit)
            if (not self.show_account_zero and initial_balance == 0 and
                    total_credit == 0 and total_debit == 0):
                return
            else:
                item_lines.append({
                    'credit': total_credit,
                    'debit': total_debit,
                    'balance': total_debit - total_credit,
                    'initial_balance': initial_balance,
                    'final_balance': final_balance,
                    # 'product_id': line.product_id.name,
                    # 'partner_id': line.partner_id.name,
                    # 'journal_id': line.journal_id.name,
                    # 'tag': line.name,
                    # 'analytic_account_id': line.analytic_account_id.name
                    # Utiliza el ID de la línea como identificador único
                })
                # initial_balance = final_balance

        return item_lines if item_lines else []

    def get_initial_balance(self, account, group_value, start_date):
        """Calculate initial balance up to the start date for the given
           group."""
        domain = [
            ('account_id', '=', account.id),
            ('date', '<', start_date),
        ]

        group_by_field = self.get_group_by_field(account)
        if group_value and group_by_field:
            if group_by_field == 'name':
                domain.append((group_by_field, '=', group_value))
            else:
                domain.append((group_by_field, '=', group_value[:-1]))
        elif not group_value and group_by_field:
            domain.append((group_by_field, '=', False))
        if account.code[:3] == '129':
            # domain67 = [
            #     ('account_id.group_id.account_group_01_id', 'in',
            #       [('6', '7')]),
            #     ('date', '<', start_date)
            # ]
            # Buscar los grupos de cuentas de tipo 6 y 7
            accounts_6_7_ids = self.env['account.account'].search([
                '|',
                ('code', '=like', '6%'),
                ('code', '=like', '7%'),
            ]).ids

            # Buscar las líneas contables de estas cuentas
            move_lines = self.env['account.move.line'].search([
                ('account_id', 'in', accounts_6_7_ids),
                ('date', '<', start_date),
            ])

            # Sumatorio de débitos y créditos
            total_debit = sum(line.debit for line in move_lines)
            total_credit = sum(line.credit for line in move_lines)
            amlines = self.env['account.move.line'].search_read(
                domain=domain,
                fields=['debit', 'credit'],
            )
            # amline_account_6_7 = self.env['account.move.line'].search_read(
            #     domain=domain67,
            #     fields=['debit', 'credit']
            # )
            initial_balance = sum(
                line['debit'] - line['credit'] for line in amlines)
            initial_balance_129 = total_debit - total_credit
            initial_balance += initial_balance_129
        else:
            amlines = self.env['account.move.line'].search_read(
                domain=domain,
                fields=['debit', 'credit'],
            )

            initial_balance = sum(
                line['debit'] - line['credit'] for line in amlines)
            if self.is_root_account_6_7(account):
                initial_balance = 0

        return initial_balance

    def is_root_account_6_7(self, account):
        # Recorre la jerarquía de padres
        if (account.code[:1] == '6' or account.code[:1] == '7'):
            return True
        return False
    # @api.multi
    # def button_export_pdf(self):
    #     data = {
    #         'date_from': self.date_from,
    #         'date_to': self.date_to,
    #         'company_id': self.company_id.id,
    #     }
    #     res = self.env.ref(
    #         'account_financial_report_qweb_add_filters.'
    #         'report_general_ledger_balance_grouped').report_action(
    #         self, data=data)
    #     return res

    @api.multi
    def button_export_pdf(self):
        self.ensure_one()
        return self.env['report'].get_action(
            self, 'account_financial_report_qweb_add_filters.'
            'template_report_trial_balance')

    def button_export_excel(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/report/trial_balance_excel/{}'.format(self.id),
            'target': 'new',
        }
