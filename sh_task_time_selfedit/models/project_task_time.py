# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import re
from odoo import models, fields, api, _, exceptions
from datetime import datetime, timedelta


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'


    tasktime_observations = fields.Text(
        string="Observations",
        help="This field is required if tasktime is modified or it is "
             "created by user. "
             "Min. 6 chars.",)

    tasktime_edited = fields.Boolean(
        string="Edited",
        default=False,
        readonly=True)
    
    tasktime_modificated = fields.Boolean(
        string="Modified",
        default=False)
    
    original_time_line = fields.Float(
        string="Initial Quantity", default=0.0)

    @api.depends('tasktime_edited')
    def _compute_tasktime_edited_show(self):
        for record in self:
            if record.tasktime_edited:
                record.tasktime_edited_show = True

    @api.onchange('unit_amount')
    def onchange_unit_amount(self):
        for record in self:
            att_admin = record.env.user.has_group(
                'hr_timesheet.group_hr_timesheet_user')
            current_att = record.env['account.analytic.line'].browse(
                record._origin.id)
            tasktime_modificated = False
            if current_att.id and record.start_date and record.end_date:
                if current_att.unit_amount != record.unit_amount:
                    current_att.write({'tasktime_edited': True})
                    tasktime_modificated = True
                    record.tasktime_modificated = tasktime_modificated
                else:
                    record.tasktime_modificated = False

    @api.constrains('tasktime_observations')
    def _check_tasktime_observations_length(self):
        for record in self:
            att_admin = record.env.user.has_group(
                'hr_timesheet.group_hr_timesheet_user')
            if (record.tasktime_modificated and
                    not record.tasktime_observations and not att_admin):
                raise exceptions.ValidationError(
                    _('The field observations must be filled.'))
            if record.tasktime_observations:
                att_obs = record.tasktime_observations.replace(' ', '')
                if (len(att_obs) < 6 or
                        len(record.tasktime_observations) < 6) and not \
                        att_admin:
                    raise exceptions.ValidationError(
                        _('The length of observations must be at least 6 '
                          'characters.'))

    @api.model
    def create(self, vals):
        if ('tasktime_observations' in vals and
                vals['tasktime_observations']):
            att_obs = vals['tasktime_observations'].lstrip().rstrip()
            att_obs = re.sub(' +', ' ', att_obs)
            vals['tasktime_observations'] = att_obs
        return super(AccountAnalyticLine, self).create(vals)

    def write(self, vals):
        resp = super(AccountAnalyticLine, self).write(vals)
        for record in self:
            if ('tasktime_observations' in vals and
                    vals['tasktime_observations']):
                att_obs = vals['tasktime_observations'].lstrip().rstrip()
                att_obs = re.sub(' +', ' ', att_obs)
                vals['tasktime_observations'] = att_obs
            if ('end_date' in vals) and vals['amount']:
                record.original_time_line = vals['amount']
            resp = super(AccountAnalyticLine, record).write(vals)
        return resp
