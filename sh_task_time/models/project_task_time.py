# Copyright (C) Softhealer Technologies.

from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    start_date = fields.Datetime("Start Date", readonly=True)
    end_date = fields.Datetime("End Date", readonly=True)


class TaskTimeAccountLine(models.Model):
    _name = 'task.time.account.line'
    _description = 'Task Time Account Line'

    def _get_default_start_time(self):
        active_model = self.env.context.get('active_model')
        if active_model == 'project.task':
            active_id = self.env.context.get('active_id')
            if active_id:
                task_search = self.env['project.task'].search(
                    [('id', '=', active_id)], limit=1)
                return task_search.start_time

    def _get_default_end_time(self):
        return datetime.now()

    def _get_default_duration(self):
        active_model = self.env.context.get('active_model')
        if active_model == 'project.task':
            active_id = self.env.context.get('active_id')
            if active_id:
                task_search = self.env['project.task'].search(
                    [('id', '=', active_id)], limit=1)
                diff = fields.Datetime.from_string(fields.Datetime.now(
                )) - fields.Datetime.from_string(task_search.start_time)
                if diff:
                    duration = float(diff.days) * 24 + \
                        (float(diff.seconds) / 3600)
                    return round(duration, 2)

    name = fields.Char("Description", required=True)
    start_date = fields.Datetime(
        "Start Date", default=_get_default_start_time, readonly=True)
    end_date = fields.Datetime(
        "End Date", default=_get_default_end_time, readonly=True)
    duration = fields.Float(
        "Duration (HH:MM)", default=_get_default_duration, readonly=True)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)

    def end_task(self):
        context = dict(self.env.context or {})
        active_model = context.get('active_model', False)
        active_id = context.get('active_id', False)

        vals = {'name': self.name, 'unit_amount': self.duration,
                'amount': self.duration, 'date': datetime.now()}
        task_search = False
        if active_model == 'project.task':
            if active_id:
                task_search = self.env['project.task'].search(
                    [('id', '=', active_id)], limit=1)

                if task_search:
                    vals.update({'start_date': task_search.start_time})
                    vals.update({'end_date': datetime.now()})
                    vals.update({'task_id': task_search.id})

                    if task_search.project_id:
                        vals.update({'project_id': task_search.project_id.id})
                        act_id = self.env['project.project'].sudo().browse(
                            task_search.project_id.id).analytic_account_id

                        if act_id:
                            vals.update({'account_id': act_id.id})

        timesheet_line = self.env['account.analytic.line'].sudo().search(
            [('task_id', '=', task_search.id),
             ('end_date', '=', False)], limit=1)
        if timesheet_line:
            timesheet_line.write(vals)
            if task_search:
                task_search.sudo().write({
                    'start_time': False,
                    'duration': 0.0,
                    'task_running': False,
                    'starter_user_id': None})
        self.sudo()._cr.commit()
        return {'type': 'ir.actions.client', 'tag': 'reload'}


class ProjectTask(models.Model):
    _inherit = 'project.task'

    start_time = fields.Datetime("Start Time", copy=False)
    end_time = fields.Datetime("End Time", copy=False)
    total_time = fields.Char("Total Time", copy=False)
    duration = fields.Float('Real Duration', compute='_compute_duration')
    task_running = fields.Boolean("Task Running", copy=False)
    starter_user_id = fields.Many2one(
        string='User starter',
        comodel_name='res.users',
        index=True,
        ondelete='restrict',
        copy=False,)

    @api.model
    def get_duration(self, task):
        if task:
            task = self.sudo().browse(int(task))
            if task and task.start_time:
                diff = fields.Datetime.from_string(
                    fields.Datetime.now()) - \
                    fields.Datetime.from_string(task.start_time)
                if diff:
                    duration = float(diff.days) * 24 + \
                        (float(diff.seconds) / 3600)
                    return diff.total_seconds() * 1000

    @api.depends('timesheet_ids.unit_amount')
    def _compute_duration(self):
        for rec in self:
            rec.duration = 0.0
            if rec and rec.timesheet_ids:
                timesheet_line = rec.timesheet_ids.filtered(
                    lambda x: x.task_id.id == rec.id and
                    x.end_date is False and x.start_date is not False)
                if timesheet_line:
                    rec.duration = timesheet_line[0].unit_amount

    def action_task_start(self):
        if self.task_running:
            raise UserError(
                _(" This task has been already started by another user !"))
        current_user_id = self.env.user.id
        # Updated to ensure only tasks of employee are checked
        running_task = self.env['project.task'].sudo().search(
            [('task_running', '=', True),
             ('id', '!=', self.id),
             ('starter_user_id', '=', current_user_id)], limit=1)
        if not self.env.company.sh_multiple_task and running_task:
            raise UserError(_("You can not start 2 tasks at same time !"))
        self.sudo().start_time = datetime.now()
        vals = {'name': '/', 'date': datetime.now()}

        if self:
            vals.update({'start_date': datetime.now()})
            vals.update({'task_id': self.id})

            if self.project_id:
                vals.update({'project_id': self.project_id.id})
                act_id = self.env['project.project'].sudo().browse(
                    self.project_id.id).analytic_account_id

                if act_id:
                    vals.update({'account_id': act_id.id})
        if current_user_id:
            emp_search = self.env['hr.employee'].search(
                [('user_id', '=', current_user_id)], limit=1)
            if emp_search:
                vals.update({
                    'employee_id': emp_search.id, })
        self.env['account.analytic.line'].sudo().create(vals)
        self.sudo().write({'task_running': True,
                           'starter_user_id': current_user_id})
        self.sudo()._cr.commit()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_task_end(self):
        self.sudo().end_time = datetime.now()
        tot_sec = (self.end_time - self.start_time).total_seconds()
        tot_hours = round((tot_sec / 3600.0), 2)

        self.sudo().total_time = tot_hours
        if self.env.company.sh_is_default_description:
            return {
                'name': "End Task",
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'task.time.account.line',
                'context': {
                    'default_name': str(self.env.user.name) +
                        ' - ' + str(self.name)},
                'target': 'new',
            }
        else:
            return {
                'name': "End Task",
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'task.time.account.line',
                'target': 'new',
            }
