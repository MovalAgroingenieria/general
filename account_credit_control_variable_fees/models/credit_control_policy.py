# -*- coding: utf-8 -*-
# 2021 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import models, fields, api


class CreditControlPolicyLevel(models.Model):
    _inherit = "credit.control.policy.level"

    variable_fees_percentage = fields.Integer(
        string="Variable fees (%)",
        help="The percentage of increase in debt at this level. It only "
             "applies if the option 'Apply variable charges' is marked in the "
             "bank journal to which the credit control line belongs.")

    custom_text_after_variable_fees = fields.Html(
        string='Custom Message after variable fees',
        translate=True,
        help="The message to explain the reason for the increase in debt.")

    print_summary_table = fields.Boolean(
        string="Print summary table",
        default=True,)

    show_invoiced_amount_column = fields.Boolean(
        string="Show invoiced amount column",
        default=True,
        help="Show the invoiced amount column in the summary table")

    show_fees_column = fields.Boolean(
        string="Show fees column",
        default=True,
        help="Show the fees column in the summary table")

    _sql_constraints = [
        ('valid_variable_fees_percentage',
         'CHECK (variable_fees_percentage >= 0)',
         'The variable fees percentage must be a value zero or positive.'),
        ]


class CreditControlLine(models.Model):
    _inherit = "credit.control.line"

    variable_fees_percentage = fields.Integer(
        compute="_compute_variable_fees_percentage")

    variable_fees = fields.Float(
        string="Variable fees",
        compute="_compute_variable_fees")

    total_amount_with_fees = fields.Float(
        string="Total amount",
        compute="_compute_total_amount_with_fees")

    @api.multi
    def _compute_variable_fees_percentage(self):
        for record in self:
            record.variable_fees_percentage = \
                record.policy_level_id.variable_fees_percentage

    # @INFO: balance_due_total is introduce by dunning_fees module
    @api.depends('variable_fees_percentage', 'balance_due_total')
    def _compute_variable_fees(self):
        for record in self:
            variable_fees = 0
            if record.variable_fees_percentage > 0 and \
                    record.balance_due_total > 0 and \
                    record.move_line_id.journal_id.apply_variable_fees is True:
                factor = float(record.variable_fees_percentage) / 100
                variable_fees = factor * record.balance_due_total
            record.variable_fees = variable_fees

    @api.depends('variable_fees', 'balance_due_total')
    def _compute_total_amount_with_fees(self):
        for record in self:
            if record.move_line_id.journal_id.apply_variable_fees is True:
                record.total_amount_with_fees = \
                    record.variable_fees + record.balance_due_total
            else:
                record.total_amount_with_fees = record.balance_due_total


class CreditCommunication(models.TransientModel):
    _inherit = "credit.control.communication"

    variable_fees_percentage = fields.Integer(
        compute="_compute_variable_fees_percentage")

    print_summary_table = fields.Boolean(
        compute="_compute_print_summary_table",
        default=True,)

    show_invoiced_amount_column = fields.Boolean(
        compute="_compute_show_invoiced_amount_column",
        default=True,)

    show_fees_column = fields.Boolean(
        compute="_compute_show_fees_column",
        default=True,)

    @api.multi
    def _compute_variable_fees_percentage(self):
        for record in self:
            record.variable_fees_percentage = \
                record.current_policy_level.variable_fees_percentage

    @api.multi
    def _compute_print_summary_table(self):
        for record in self:
            record.print_summary_table = \
                record.current_policy_level.print_summary_table

    @api.multi
    def _compute_show_invoiced_amount_column(self):
        for record in self:
            record.show_invoiced_amount_column = \
                record.current_policy_level.show_invoiced_amount_column

    @api.multi
    def _compute_show_fees_column(self):
        for record in self:
            record.show_fees_column = \
                record.current_policy_level.show_fees_column
