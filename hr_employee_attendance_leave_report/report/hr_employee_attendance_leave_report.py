# 2022 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import locale
import pytz
import re
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import fields, api, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import get_lang


class HrEmployeeAttendanceLeaveReport(models.AbstractModel):
    _name = 'report.hr_employee_attendance_leave_report.att_lea_template'
    _description = 'Employee Attendances / Leaves Report'

    def _get_data_from_wizard(self, data):
        res = []
        res.append({'data': []})
        timezone = \
            self._context.get('tz') or self.env.user.partner_id.tz or 'UTC'
        self_tz = self.with_context(tz=timezone)
        lang = get_lang(self.env)
        time_format = '%H:%M'
        report_date = fields.Datetime.context_timestamp(
            self_tz, fields.Datetime.from_string(data['report_date']))
        report_date = report_date.strftime(lang.date_format) + '  [' + \
            report_date.strftime(time_format) + ']'
        start_date = fields.Datetime.context_timestamp(
            self_tz, fields.Datetime.from_string(data['start_date']))
        start_date_show = start_date.strftime(lang.date_format) + '  [' + \
            start_date.strftime(time_format) + ']'
        end_date = fields.Datetime.context_timestamp(
            self_tz, fields.Datetime.from_string(data['end_date']))
        end_date_show = end_date.strftime(lang.date_format) + '  [' + \
            end_date.strftime(time_format) + ']'
        res[0]['data'].append({
            'report_date': report_date,
            'start_date': start_date,
            'start_date_show': start_date_show,
            'end_date': end_date,
            'end_date_show': end_date_show,
            'employee_ids': data['employee_ids'],
            })
        return res

    def _get_employee_data(self, employee_id):
        employee = False
        if employee_id:
            employee = self.env['hr.employee'].browse(employee_id)
        return employee

    def get_formatted_date(self, date):
        date_without_tz = date.replace(tzinfo=None)
        return date_without_tz

    def get_formatted_date_show(self, date):
        date_without_tz = date.replace(tzinfo=None)
        user_tz = self.env.user.tz or pytz.utc
        local = pytz.timezone(user_tz)
        user_tz_date = date_without_tz.astimezone(local)
        user_tz_date = re.sub(r"([+-])([0-9]{2}):([0-9]{2})", "\\1\\2\\3",
                              str(date_without_tz.astimezone(local)), 0)
        formatted_user_tz_date = datetime.strptime(str(user_tz_date),
                                                   "%Y-%m-%d %H:%M:%S%z")\
            .strftime("%d/%m/%Y  [%H:%M]")
        return formatted_user_tz_date

    def get_difference(self, check_in, check_out):
        check_in = self.get_formatted_date(check_in)
        check_out = self.get_formatted_date(check_out)
        difference = relativedelta(check_out, check_in)
        hours = difference.hours
        minutes = difference.minutes
        difference_time = str(hours).zfill(2) + ':' + str(minutes).zfill(2)
        return difference_time, difference

    def get_translated_weekday(self, day_num):
        translated_weekday = ""
        if day_num == 0:
            translated_weekday = _('Monday')
        if day_num == 1:
            translated_weekday = _('Tuesday')
        if day_num == 2:
            translated_weekday = _('Wednesday')
        if day_num == 3:
            translated_weekday = _('Thursday')
        if day_num == 4:
            translated_weekday = _('Friday')
        if day_num == 5:
            translated_weekday = _('Saturday')
        if day_num == 6:
            translated_weekday = _('Sunday')
        return translated_weekday

    def _get_attendance_data(self, employee_id, start_date, end_date):
        data = []
        start = self.get_formatted_date(start_date)
        end = self.get_formatted_date(end_date)
        attendance_ids = self.env['hr.attendance'].search(
            [('check_in', '>=', str(start)), ('check_out', '<=', str(end)),
             ('employee_id', '=', employee_id)], order='check_in')
        if attendance_ids:
            difference_time = ''
            total_working_time = relativedelta(
                days=0, hours=0, minutes=0, seconds=0)
            total_working_time_show = ''
            for attendance in attendance_ids:
                check_in = self.get_formatted_date(attendance.check_in)
                check_out = ''
                check_in_show = self.get_formatted_date_show(
                    attendance.check_in)
                check_in_weekday = self.get_translated_weekday(
                    attendance.check_in.weekday())
                check_in_show = check_in_show + ' - ' + check_in_weekday
                check_out_show = ''
                if attendance.check_out:
                    check_out = \
                        self.get_formatted_date(attendance.check_out)
                    difference_time, difference = \
                        self.get_difference(check_in, check_out)
                    total_working_time += difference
                    days_in_hours = total_working_time.days * 24
                    total_hours = days_in_hours + total_working_time.hours
                    if total_hours < 10:
                        total_hours = str(total_hours).zfill(2)
                    else:
                        total_hours = str(total_hours)
                    total_working_time_show = total_hours + ':' + \
                        str(total_working_time.minutes).zfill(2)
                    check_out_show = self.get_formatted_date_show(
                        attendance.check_out)
                    check_out_weekday = self.get_translated_weekday(
                        attendance.check_out.weekday())
                    check_out_show = check_out_show + ' - ' + check_out_weekday
                data.append(
                    {'check_in': check_in_show,
                     'check_out': check_out_show,
                     'difference': difference_time,
                     'total_working_time_show': total_working_time_show})
        return data

    def _get_leaves_data(self, employee_id, start_date, end_date):
        data = []
        start = self.get_formatted_date(start_date)
        end = self.get_formatted_date(end_date)
        results = []
        employee_leaves = self.env['hr.leave'].search(
            [('employee_id', '=', employee_id),
             ('holiday_type', '=', 'employee'),
             ('state', '!=', 'cancel')], order='date_from')
        for employee_leave in employee_leaves:
            from_date = self.get_formatted_date(employee_leave.date_from)
            to_date = self.get_formatted_date(employee_leave.date_to)
            if from_date >= start and from_date <= end:
                results.append(employee_leave)
            elif to_date >= start and to_date <= end:
                results.append(employee_leave)
        if results:
            for leave_id in results:
                from_date_weekday = self.get_translated_weekday(
                    from_date.weekday())
                from_date_show = \
                    self.get_formatted_date_show(leave_id.date_from)
                from_date_show = from_date_show + ' - ' + from_date_weekday
                to_date_weekday = self.get_translated_weekday(
                    to_date.weekday())
                to_date_show = self.get_formatted_date_show(leave_id.date_to)
                to_date_show = to_date_show + ' - ' + to_date_weekday
                total_num_of_days = self.transform_float_to_locale(
                    abs(leave_id.number_of_days), 2)
                from_date_2 = self.get_formatted_date(leave_id.date_from)
                to_date_2 = self.get_formatted_date(leave_id.date_to)
                if start < from_date_2 and end > to_date_2:
                    period_num_of_days = total_num_of_days
                elif start < from_date_2:
                    difference = relativedelta(from_date_2, end)
                    total_seconds = \
                        abs((difference.days * 24 * 3600) + (
                            difference.hours * 3600) + (
                                difference.minutes * 60) + difference.seconds)
                    diff_days = total_seconds / 86400.0
                    period_num_of_days = self.transform_float_to_locale(
                        diff_days, 2)
                elif end > to_date_2:
                    difference = relativedelta(start, to_date_2)
                    total_seconds = \
                        abs((difference.days * 24 * 3600) + (
                            difference.hours * 3600) + (
                                difference.minutes * 60) + difference.seconds)
                    diff_days = total_seconds / 86400.0
                    period_num_of_days = self.transform_float_to_locale(
                        diff_days, 2)
                data.append({'type': leave_id.holiday_status_id.name,
                             'state': leave_id.state,
                             'from': from_date_show,
                             'to': to_date_show,
                             'reason': leave_id.name,
                             'total_num_of_days': total_num_of_days,
                             'period_num_of_days': period_num_of_days})
        return data

    def _get_public_holidays_data(self, start_date, end_date):
        data = []
        start = self.get_formatted_date(start_date)
        end = self.get_formatted_date(end_date)
        public_holidays = self.env['hr.holidays.public.line'].search(
            [('date', '>=', str(start)), ('date', '<=', str(end))],
            order='date')
        if public_holidays:
            for public_holiday in public_holidays:
                holiday_date = public_holiday.date.strftime("%d/%m/%Y")
                holiday_date_weekday = self.get_translated_weekday(
                    public_holiday.date.weekday())
                holiday_date = holiday_date + ' - ' + holiday_date_weekday
                data.append(
                    {'holiday_date': holiday_date,
                     'holiday_name': public_holiday.name})
        return data

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form'):
            raise UserError(
                _("Form content is missing, this report cannot be printed."))
        attendance_leave_report = \
            self.env['ir.actions.report']._get_report_from_name(
                'hr_employee_attendance_leave_report.'
                'employee_attendance_leave_print_report')
        docs = self.env['hr.employee'].browse(data['form']['employee_ids'])
        return {
            'doc_ids': self.ids,
            'doc_model': attendance_leave_report.model,
            'docs': docs,
            'get_data_from_wizard': self._get_data_from_wizard(data['form']),
            'get_employee_data': self._get_employee_data,
            'get_attendance_data': self._get_attendance_data,
            'get_leaves_data': self._get_leaves_data,
            'get_public_holidays_data': self._get_public_holidays_data,
        }

    @api.model
    def transform_float_to_locale(self, float_number, precision):
        precision = '%.' + str(precision) + 'f'
        locale.setlocale(locale.LC_NUMERIC,
                         str(self.env.context['lang'] + '.utf8'))
        formated_float_number = locale.format(precision, float_number, True)
        locale.resetlocale(locale.LC_NUMERIC)
        return formated_float_number
