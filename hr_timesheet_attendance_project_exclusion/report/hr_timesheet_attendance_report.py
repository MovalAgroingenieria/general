# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, tools


class TimesheetAttendance(models.Model):
    _inherit = 'hr.timesheet.attendance.report'

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self._cr.execute("""CREATE OR REPLACE VIEW %s AS (
            SELECT
                max(id) AS id,
                t.user_id,
                t.date,
                coalesce(sum(t.attendance), 0) AS total_attendance,
                coalesce(sum(t.timesheet), 0) AS total_timesheet,
                coalesce(sum(t.attendance), 0) - coalesce(sum(t.timesheet), 0) as total_difference
            FROM (
                SELECT
                    -hr_attendance.id AS id,
                    resource_resource.user_id AS user_id,
                    hr_attendance.worked_hours AS attendance,
                    NULL AS timesheet,
                    hr_attendance.check_in::date AS date
                FROM hr_attendance
                LEFT JOIN hr_employee ON hr_employee.id = hr_attendance.employee_id
                LEFT JOIN resource_resource on resource_resource.id = hr_employee.resource_id
            UNION ALL
                SELECT
                    ts.id AS id,
                    ts.user_id AS user_id,
                    NULL AS attendance,
                    ts.unit_amount AS timesheet,
                    ts.date AS date
                FROM account_analytic_line AS ts
                INNER JOIN project_project pp
                ON ts.project_id = pp.id
                WHERE ts.project_id IS NOT NULL and
                pp.excluded_from_attendance_report = false
            ) AS t
            GROUP BY t.user_id, t.date
            ORDER BY t.date
        )
        """ % self._table)
