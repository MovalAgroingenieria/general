# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import email_split, float_is_zero


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"


    def action_submit_sheet(self):
        activities = self.env['ir.config_parameter'].sudo().get_param(
            'hr_expense_activities.with_activity',
            default='False'
        )
        if activities == 'False':
            self.write({'state': 'submit'})
        else:
            super(HrExpenseSheet, self).action_submit_sheet()
