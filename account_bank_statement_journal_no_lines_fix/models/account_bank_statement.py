# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Journal',
        compute='_compute_journal_id',
        store=True,
        readonly=False,
        check_company=True,
        required=True,
    )

    date = fields.Date(
        compute='_compute_date_index',
        store=True,
        readonly=False,
        index=True,
        default=fields.Date.context_today,
    )

    @api.depends('line_ids.journal_id')
    def _compute_journal_id(self):
        """
        Compute journal_id from statement lines only if not manually set.
        This allows manual selection of journal when creating new statements.
        """
        for statement in self:
            if not statement.journal_id and statement.line_ids:
                statement.journal_id = statement.line_ids.journal_id

    @api.depends('line_ids.internal_index', 'line_ids.state')
    def _compute_date_index(self):
        """
        Override to ensure date is always set, using today if no lines exist.
        """
        for stmt in self:
            sorted_lines = stmt.line_ids.filtered("internal_index").sorted(
                'internal_index')
            stmt.first_line_index = sorted_lines[:1].internal_index
            posted_lines = sorted_lines.filtered(
                lambda line: line.state == 'posted')
            computed_date = posted_lines[-1:].date
            if computed_date:
                stmt.date = computed_date
            elif not stmt.date:
                stmt.date = fields.Date.context_today(stmt)

    @api.model
    def default_get(self, fields_list):
        """
        Override default_get to set a default journal from context or the
        first bank journal. Also set default balance_start from previous
        statement.
        """
        defaults = super().default_get(fields_list)

        if 'journal_id' in fields_list and not defaults.get('journal_id'):
            journal_id = self._context.get('default_journal_id')
            if not journal_id:
                journal = self.env['account.journal'].search([
                    ('type', 'in', ['bank', 'cash']),
                    ('company_id', '=', self.env.company.id),
                ], limit=1)
                if journal:
                    journal_id = journal.id

            if journal_id:
                defaults['journal_id'] = journal_id
                if ('balance_start' in fields_list and
                        not defaults.get('balance_start')):
                    last_statement = self.search([
                        ('journal_id', '=', journal_id),
                    ], order='date desc, id desc', limit=1)
                    if last_statement and last_statement.balance_end_real:
                        defaults['balance_start'] = (
                            last_statement.balance_end_real)
        return defaults

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        """
        Update statement lines journal when statement journal changes.
        Also auto-set balance_start from last statement of selected journal.
        """
        if self.journal_id:
            if self.line_ids:
                for line in self.line_ids:
                    line.journal_id = self.journal_id
            if not self.balance_start:
                last_statement = self.search([
                    ('journal_id', '=', self.journal_id.id),
                    ('id', '!=', self.id or 0),
                ], order='date desc, id desc', limit=1)
                if last_statement and last_statement.balance_end_real:
                    self.balance_start = last_statement.balance_end_real

    @api.onchange('balance_start', 'balance_end_real')
    def _onchange_balance_fields(self):
        """
        Help user by suggesting balance_end_real when balance_start changes.
        """
        if self.balance_start and not self.balance_end_real:
            self.balance_end_real = self.balance_start

    @api.depends('balance_start', 'balance_end_real', 'line_ids.amount',
                 'line_ids.state')
    def _compute_balance_end(self):
        """
        Override to handle statements without lines properly.
        """
        for stmt in self:
            lines = stmt.line_ids.filtered(lambda x: x.state == 'posted')
            if lines:
                stmt.balance_end = stmt.balance_start + sum(
                    lines.mapped('amount'))
            else:
                stmt.balance_end = stmt.balance_end_real or stmt.balance_start

    @api.depends('balance_start', 'line_ids')
    def _compute_balance_end_real(self):
        """
        Override to handle statements without lines properly.
        """
        for stmt in self:
            if not stmt.line_ids:
                if not stmt.balance_end_real or stmt.balance_end_real == 0:
                    stmt.balance_end_real = stmt.balance_start

    @api.depends('balance_end', 'balance_end_real', 'line_ids.amount',
                 'line_ids.state', 'balance_start', 'journal_id')
    def _compute_is_complete(self):
        """
        Override to handle statements without lines properly.
        For statements without lines, check that balance_start equals
        balance_end_real of the previous statement.
        For statements with lines, use standard logic.
        """
        for stmt in self:
            posted_lines = stmt.line_ids.filtered(
                lambda line: line.state == 'posted')

            if not posted_lines:
                if stmt.journal_id and stmt.date:
                    domain = [
                        ('journal_id', '=', stmt.journal_id.id),
                        ('date', '<', stmt.date)
                    ]
                    previous_statement = self.search(
                        domain, order='date desc, id desc', limit=1)
                    if (not previous_statement and stmt.id and
                            str(stmt.id).isdigit()):
                        same_date_domain = [
                            ('journal_id', '=', stmt.journal_id.id),
                            ('date', '=', stmt.date),
                            ('id', '<', stmt.id)
                        ]
                        previous_statement = self.search(
                            same_date_domain, order='id desc', limit=1)

                    if previous_statement:
                        stmt.is_complete = stmt.currency_id.compare_amounts(
                            stmt.balance_start,
                            previous_statement.balance_end_real) == 0
                    else:
                        stmt.is_complete = True
                else:
                    stmt.is_complete = False
            else:
                stmt.is_complete = (posted_lines and
                                    stmt.currency_id.compare_amounts(
                                        stmt.balance_end,
                                        stmt.balance_end_real) == 0)

    def _recompute_related_statements(self):
        """
        Recompute is_complete for statements that might be affected by changes
        to this statement.
        """
        if not self.journal_id or not self.date:
            return
        domain = [
            ('journal_id', '=', self.journal_id.id),
            ('date', '>=', self.date)
        ]
        if self.id and str(self.id).isdigit():
            domain = [
                ('journal_id', '=', self.journal_id.id),
                '|',
                ('date', '>', self.date),
                '&',
                ('date', '=', self.date),
                ('id', '>', self.id)
            ]
        affected_statements = self.search(domain)
        if affected_statements:
            affected_statements._compute_is_complete()

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create to recompute related statements.
        """
        statements = super().create(vals_list)
        for statement in statements:
            statement._recompute_related_statements()
        return statements

    def write(self, vals):
        """
        Override write to recompute related statements when relevant
        fields change.
        """
        result = super().write(vals)
        relevant_fields = ['date', 'journal_id', 'balance_end_real',
                           'balance_start']
        if any(field in vals for field in relevant_fields):
            for statement in self:
                statement._recompute_related_statements()
        return result
