# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import contextlib
import locale
import re
from datetime import datetime

import pytz
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import get_lang


class HrEmployeeAttendanceLeaveReport(models.AbstractModel):
    _name = "report.hr_employee_attendance_leave_report.att_lea_template"
    _description = "Employee Attendances / Leaves Report"

    def _get_data_from_wizard(self, data):
        res = []
        res.append({"data": []})
        timezone = self._context.get("tz") or self.env.user.partner_id.tz or "UTC"
        self_tz = self.with_context(tz=timezone)
        lang = get_lang(self.env)
        time_format = "%H:%M"
        report_date = fields.Datetime.context_timestamp(
            self_tz, fields.Datetime.to_datetime(data["report_date"])
        )
        report_date = (
            report_date.strftime(lang.date_format)
            + "  ["
            + report_date.strftime(time_format)
            + "]"
        )
        start_date = fields.Datetime.context_timestamp(
            self_tz, fields.Datetime.to_datetime(data["start_date"])
        )
        start_date_show = (
            start_date.strftime(lang.date_format)
            + "  ["
            + start_date.strftime(time_format)
            + "]"
        )
        end_date = fields.Datetime.context_timestamp(
            self_tz, fields.Datetime.to_datetime(data["end_date"])
        )
        end_date_show = (
            end_date.strftime(lang.date_format)
            + "  ["
            + end_date.strftime(time_format)
            + "]"
        )
        res[0]["data"].append(
            {
                "report_date": report_date,
                "start_date": start_date,
                "start_date_show": start_date_show,
                "end_date": end_date,
                "end_date_show": end_date_show,
                "employee_ids": data["employee_ids"],
            }
        )
        return res

    def _get_employee_data(self, employee_id):
        employee = False
        if employee_id:
            employee = self.env["hr.employee"].browse(employee_id)
        return employee

    def get_formatted_date(self, date):
        date_without_tz = date.replace(tzinfo=None)
        return date_without_tz

    def get_formatted_date_show(self, date):
        date_without_tz = date.replace(tzinfo=None)
        user_tz_name = self.env.user.tz or "UTC"
        local = pytz.timezone(user_tz_name)
        user_tz_date = date_without_tz.astimezone(local)
        user_tz_date = re.sub(
            r"([+-])([0-9]{2}):([0-9]{2})",
            "\\1\\2\\3",
            str(date_without_tz.astimezone(local)),
            0,
        )
        formatted_user_tz_date = datetime.strptime(
            str(user_tz_date), "%Y-%m-%d %H:%M:%S%z"
        ).strftime("%d/%m/%Y  [%H:%M]")
        return formatted_user_tz_date

    def get_difference(self, check_in, check_out):
        check_in = self.get_formatted_date(check_in)
        check_out = self.get_formatted_date(check_out)
        difference = relativedelta(check_out, check_in)
        hours = difference.hours
        minutes = difference.minutes
        difference_time = str(hours).zfill(2) + ":" + str(minutes).zfill(2)
        return difference_time, difference

    def get_translated_weekday(self, day_num):
        translated_weekday = ""
        if day_num == 0:
            translated_weekday = self.env._("Monday")
        if day_num == 1:
            translated_weekday = self.env._("Tuesday")
        if day_num == 2:
            translated_weekday = self.env._("Wednesday")
        if day_num == 3:
            translated_weekday = self.env._("Thursday")
        if day_num == 4:
            translated_weekday = self.env._("Friday")
        if day_num == 5:
            translated_weekday = self.env._("Saturday")
        if day_num == 6:
            translated_weekday = self.env._("Sunday")
        return translated_weekday

    def _get_attendance_data(self, employee_id, start_date, end_date):
        data = []
        start = self.get_formatted_date(start_date)
        end = self.get_formatted_date(end_date)
        attendance_ids = self.env["hr.attendance"].search(
            [
                ("check_in", ">=", str(start)),
                ("check_out", "<=", str(end)),
                ("employee_id", "=", employee_id),
            ],
            order="check_in",
        )
        if attendance_ids:
            difference_time = ""
            total_working_time = relativedelta(days=0, hours=0, minutes=0, seconds=0)
            total_working_time_show = ""
            for attendance in attendance_ids:
                check_in = self.get_formatted_date(attendance.check_in)
                check_out = ""
                check_in_show = self.get_formatted_date_show(attendance.check_in)
                check_in_weekday = self.get_translated_weekday(
                    attendance.check_in.weekday()
                )
                check_in_show = check_in_show + " - " + check_in_weekday
                check_out_show = ""
                if attendance.check_out:
                    check_out = self.get_formatted_date(attendance.check_out)
                    difference_time, difference = self.get_difference(
                        check_in, check_out
                    )
                    total_working_time += difference
                    days_in_hours = total_working_time.days * 24
                    total_hours = days_in_hours + total_working_time.hours
                    if total_hours < 10:
                        total_hours = str(total_hours).zfill(2)
                    else:
                        total_hours = str(total_hours)
                    total_working_time_show = (
                        total_hours + ":" + str(total_working_time.minutes).zfill(2)
                    )
                    check_out_show = self.get_formatted_date_show(attendance.check_out)
                    check_out_weekday = self.get_translated_weekday(
                        attendance.check_out.weekday()
                    )
                    check_out_show = check_out_show + " - " + check_out_weekday
                data.append(
                    {
                        "check_in": check_in_show,
                        "check_out": check_out_show,
                        "difference": difference_time,
                        "total_working_time_show": total_working_time_show,
                    }
                )
        return data

    def _get_leaves_data(self, employee_id, start_date, end_date):
        data = []
        start = self.get_formatted_date(start_date)
        end = self.get_formatted_date(end_date)
        results = []
        employee_leaves = self.env["hr.leave"].search(
            [
                ("employee_id", "=", employee_id),
                ("state", "!=", "cancel"),
            ],
            order="date_from",
        )
        for employee_leave in employee_leaves:
            from_date = self.get_formatted_date(employee_leave.date_from)
            to_date = self.get_formatted_date(employee_leave.date_to)
            if start <= from_date <= end:
                results.append(employee_leave)
            elif start <= to_date <= end:
                results.append(employee_leave)
        if results:
            for leave_id in results:
                from_date_weekday = self.get_translated_weekday(
                    leave_id.date_from.weekday()
                )
                from_date_show = self.get_formatted_date_show(leave_id.date_from)
                from_date_show = from_date_show + " - " + from_date_weekday
                to_date_weekday = self.get_translated_weekday(
                    leave_id.date_to.weekday()
                )
                to_date_show = self.get_formatted_date_show(leave_id.date_to)
                to_date_show = to_date_show + " - " + to_date_weekday
                total_num_of_days = self.transform_float_to_locale(
                    abs(leave_id.number_of_days), 2
                )
                from_date_2 = self.get_formatted_date(leave_id.date_from)
                to_date_2 = self.get_formatted_date(leave_id.date_to)
                if start < from_date_2 and end > to_date_2:
                    period_num_of_days = total_num_of_days
                elif start < from_date_2:
                    difference = relativedelta(from_date_2, end)
                    total_seconds = abs(
                        (difference.days * 24 * 3600)
                        + (difference.hours * 3600)
                        + (difference.minutes * 60)
                        + difference.seconds
                    )
                    diff_days = total_seconds / 86400.0
                    period_num_of_days = self.transform_float_to_locale(diff_days, 2)
                elif end > to_date_2:
                    difference = relativedelta(start, to_date_2)
                    total_seconds = abs(
                        (difference.days * 24 * 3600)
                        + (difference.hours * 3600)
                        + (difference.minutes * 60)
                        + difference.seconds
                    )
                    diff_days = total_seconds / 86400.0
                    period_num_of_days = self.transform_float_to_locale(diff_days, 2)
                else:
                    period_num_of_days = total_num_of_days
                data.append(
                    {
                        "type": leave_id.holiday_status_id.name,
                        "state": leave_id.state,
                        "from": from_date_show,
                        "to": to_date_show,
                        "reason": leave_id.name,
                        "total_num_of_days": total_num_of_days,
                        "period_num_of_days": period_num_of_days,
                    }
                )
        return data

    def _get_public_holidays_data(self, start_date, end_date):
        data = []
        start = self.get_formatted_date(start_date)
        end = self.get_formatted_date(end_date)
        start_day = start.date() if hasattr(start, "date") else start
        end_day = end.date() if hasattr(end, "date") else end
        holiday_line = self.env["calendar.public.holiday.line"].sudo()
        public_holidays = holiday_line.search(
            [("date", ">=", start_day), ("date", "<=", end_day)],
            order="date",
        )
        if public_holidays:
            for public_holiday in public_holidays:
                holiday_date = public_holiday.date.strftime("%d/%m/%Y")
                holiday_date_weekday = self.get_translated_weekday(
                    public_holiday.date.weekday()
                )
                holiday_date = holiday_date + " - " + holiday_date_weekday
                data.append(
                    {"holiday_date": holiday_date, "holiday_name": public_holiday.name}
                )
        return data

    def _get_report_labels(self):
        return {
            "title": self.env._("Attendances / Leaves Report"),
            "section_employee": self.env._("Employee"),
            "section_attendance": self.env._("Attendances"),
            "section_leave": self.env._("Leaves"),
            "section_holidays": self.env._("Public holidays"),
            "section_conformity": self.env._("Conformity"),
            "label_from": self.env._("From"),
            "label_to": self.env._("To"),
            "th_check_in": self.env._("Check-in"),
            "th_check_out": self.env._("Check-out"),
            "th_working_hours": self.env._("Working hours"),
            "total_working_hours": self.env._("Total working hours"),
            "no_attendance": self.env._(
                "No attendance was found during this period for the employee."
            ),
            "th_leave_type": self.env._("Type"),
            "th_leave_period": self.env._("From / To"),
            "th_leave_days": self.env._("Period / Total days"),
            "th_leave_reason": self.env._("Reason"),
            "non_validated_note": self.env._(
                "(*) There are non-validated leaves in the selected period."
            ),
            "no_leave": self.env._(
                "No leave was found during this period for the employee."
            ),
            "th_holiday_date": self.env._("Date"),
            "th_holiday_name": self.env._("Name"),
            "no_public_holidays": self.env._(
                "There are no public holidays for the selected period."
            ),
            "company_signature": self.env._("Company signature"),
            "employee_signature": self.env._("Employee signature"),
        }

    @api.model
    def _get_report_values(self, docids, data=None):  # pylint: disable=unused-argument
        if not data.get("form"):
            raise UserError(
                self.env._("Form content is missing, this report cannot be printed.")
            )
        attendance_leave_report = self.env["ir.actions.report"]._get_report_from_name(
            "hr_employee_attendance_leave_report.employee_attendance_leave_print_report"
        )
        docs = self.env["hr.employee"].browse(data["form"]["employee_ids"])
        return {
            "doc_ids": self.ids,
            "doc_model": attendance_leave_report.model,
            "docs": docs,
            "labels": self._get_report_labels(),
            "get_data_from_wizard": self._get_data_from_wizard(data["form"]),
            "get_employee_data": self._get_employee_data,
            "get_attendance_data": self._get_attendance_data,
            "get_leaves_data": self._get_leaves_data,
            "get_public_holidays_data": self._get_public_holidays_data,
        }

    @api.model
    def transform_float_to_locale(self, float_number, precision):
        precision_fmt = "%." + str(int(precision)) + "f"
        lang = str(self.env.context.get("lang") or self.env.user.lang or "en_US")
        loc = lang.replace("@", "_") + ".UTF-8"
        try:
            locale.setlocale(locale.LC_NUMERIC, loc)
            formated_float_number = locale.format_string(
                precision_fmt, float_number, grouping=True
            )
        except (locale.Error, ValueError, OSError):
            formated_float_number = precision_fmt % float_number
        finally:
            with contextlib.suppress(locale.Error, OSError):
                locale.setlocale(locale.LC_NUMERIC, "C")
        return formated_float_number
