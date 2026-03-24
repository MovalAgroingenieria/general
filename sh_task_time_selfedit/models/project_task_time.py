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


class ProjectTask(models.Model):
    _inherit = 'project.task'

    def action_task_start(self):
        """Override to open the end-task wizard for the running task
        instead of raising an error, so the user can enter the
        description before the new task starts automatically."""
        if self.task_running:
            raise exceptions.UserError(
                _("This task has been already started by another user!"))
        current_user_id = self.env.user.id
        running_task = self.env['project.task'].sudo().search(
            [('task_running', '=', True),
             ('id', '!=', self.id),
             ('starter_user_id', '=', current_user_id)], limit=1)
        if not self.env.company.sh_multiple_task and running_task:
            # Open the end-task wizard for the running task, passing
            # the id of the task to start after completion.
            running_task.sudo().end_time = datetime.now()
            tot_sec = (running_task.end_time -
                       running_task.start_time).total_seconds()
            tot_hours = round((tot_sec / 3600.0), 2)
            running_task.sudo().total_time = tot_hours

            ctx = {
                'active_model': 'project.task',
                'active_id': running_task.id,
                'task_to_start_id': self.id,
            }
            if self.env.company.sh_is_default_description:
                ctx['default_name'] = (str(self.env.user.name) +
                                       ' - ' + str(running_task.name))
            return {
                'name': _("End running task: %s", running_task.name),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'task.time.account.line',
                'context': ctx,
                'target': 'new',
            }

        return super().action_task_start()

    def action_task_end(self):
        """Override to prevent a user from stopping another user's
        running task."""
        if (self.task_running and self.starter_user_id
                and self.starter_user_id != self.env.user):
            raise exceptions.UserError(
                _("You cannot stop this task because it was started "
                  "by %s.", self.starter_user_id.name))
        return super().action_task_end()


class TaskTimeAccountLine(models.Model):
    _inherit = 'task.time.account.line'

    def end_task(self):
        """Override: after ending the task, if a new task was queued
        to start (via task_to_start_id in context), start it."""
        task_to_start_id = self.env.context.get('task_to_start_id', False)
        result = super().end_task()
        if task_to_start_id:
            task_to_start = self.env['project.task'].browse(task_to_start_id)
            if task_to_start.exists() and not task_to_start.task_running:
                task_to_start.action_task_start()
        return result
