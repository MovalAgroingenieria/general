# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import re
from datetime import datetime, timedelta
from odoo import models, fields, api, exceptions, _


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    attendance_observations = fields.Text(
        string="Observations",
        help="This field is required if attendance is modified or it is created outside the current time"
             "(margin 30 minutes) by user. Min. 6 chars.",
    )

    attendance_edited = fields.Boolean(
        string="Edited",
        default=False,
        readonly=True,
    )

    attendance_modificated = fields.Boolean(
        string="Modified",
        default=False,
    )

    @api.depends("attendance_edited")
    def _compute_attendance_edited_show(self):
        for record in self:
            if record.attendance_edited:
                record.attendance_edited_show = True

    @api.onchange("check_in", "check_out")
    def onchange_checkin_checkout(self):
        for record in self:
            att_admin = record.env.user.has_group("hr_attendance.group_hr_attendance_manager")
            current_att = record.env["hr.attendance"].browse(record._origin.id)
            current_time = datetime.now()
            time_limit_down = current_time - timedelta(minutes=30)
            time_limit_up = current_time + timedelta(minutes=30)
            # Detect if attendance is modified and edited or is created outside the current time range
            attendance_modificated = False
            if current_att.id and record.check_in:
                if current_att.check_in != record.check_in:
                    current_att.sudo().write({"attendance_edited": True})
                if current_att.check_in != record.check_in and not att_admin:
                    attendance_modificated = True
                    record.attendance_modificated = attendance_modificated
                    if (record.check_in < time_limit_down or record.check_in > time_limit_up) and not att_admin:
                        record.attendance_modificated = True
                    else:
                        record.attendance_modificated = False
            if current_att.id and record.check_out and current_att.check_out:
                if current_att.check_out != record.check_out:
                    current_att.sudo().write({"attendance_edited": True})
                if current_att.check_out != record.check_out and not att_admin:
                    attendance_modificated = True
                    record.attendance_modificated = attendance_modificated
            if (current_att.id and record.check_out and current_att.check_out != record.check_out):
                if (record.check_out < time_limit_down or record.check_out > time_limit_up) and not att_admin:
                    record.attendance_modificated = True
                else:
                    record.attendance_modificated = False

    @api.constrains("attendance_observations")
    def _check_attendance_observations_length(self):
        for record in self:
            att_admin = record.env.user.has_group("hr_attendance.group_hr_attendance_manager")
            if (record.attendance_modificated and
                    not record.attendance_observations and not att_admin):
                raise exceptions.ValidationError(_("The field observations must be filled."))
            if record.attendance_observations:
                att_obs = record.attendance_observations.replace(" ", "")
                if (len(att_obs) < 6 or
                        len(record.attendance_observations) < 6) and not att_admin:
                    raise exceptions.ValidationError(_("The length of observations must be at least 6 characters."))

    @api.model
    def create(self, vals):
        if ("attendance_observations" in vals and vals["attendance_observations"]):
            att_obs = vals["attendance_observations"].lstrip().rstrip()
            att_obs = re.sub(' +', ' ', att_obs)
            vals['attendance_observations'] = att_obs
        return super(HrAttendance, self).create(vals)

    def write(self, vals):
        if ("attendance_observations" in vals and vals["attendance_observations"]):
            att_obs = vals["attendance_observations"].lstrip().rstrip()
            att_obs = re.sub(' +', ' ', att_obs)
            vals["attendance_observations"] = att_obs
        return super(HrAttendance, self.sudo()).write(vals)
