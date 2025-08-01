# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import datetime

from odoo import api, models


class HrHolidaysPublic(models.Model):
    _inherit = 'hr.holidays.public'

    def _get_domain_states_filter(
        self, pholidays, start_dt, end_dt, partner_id=None
    ):
        """
        Override to avoid warning when both employee_id and partner_id are passed.
        Only use partner_id since it's already resolved.
        """
        partner = None
        if partner_id:
            partner = self.env["res.partner"].browse(partner_id)
        states_filter = [("year_id", "in", pholidays.ids)]
        if partner and partner.state_id:
            states_filter += [
                "|",
                ("state_ids", "=", False),
                ("state_ids", "=", partner.state_id.id),
            ]
        else:
            states_filter.append(("state_ids", "=", False))
        states_filter.append(("date", ">=", start_dt))
        states_filter.append(("date", "<=", end_dt))
        return states_filter

    @api.model
    @api.returns("hr.holidays.public.line")
    def get_holidays_list(
        self, year=None, start_dt=None, end_dt=None, employee_id=None, partner_id=None
    ):
        """
        Override to avoid warning when both employee_id and partner_id are passed.
        Returns recordset of hr.holidays.public.line
        for the specified year and employee
        :param year: year as string (optional if start_dt and end_dt defined)
        :param start_dt: start_dt as date
        :param end_dt: end_dt as date
        :param employee_id: ID of the employee
        :param partner_id: ID of the partner
        :return: recordset of hr.holidays.public.line
        """
        partner = self._get_partner_deprecated_employee(partner_id, employee_id)
        if not start_dt and not end_dt:
            start_dt = datetime.date(year, 1, 1)
            end_dt = datetime.date(year, 12, 31)
        years = list(range(start_dt.year, end_dt.year + 1))
        holidays_filter = [("year", "in", years)]
        if partner:
            if partner.country_id:
                holidays_filter.append("|")
                holidays_filter.append(("country_id", "=", False))
                holidays_filter.append(("country_id", "=", partner.country_id.id))
            else:
                holidays_filter.append(("country_id", "=", False))
        pholidays = self.search(holidays_filter)
        if not pholidays:
            return self.env["hr.holidays.public.line"]
        partner_id = partner.id if partner else None
        # Only pass partner_id to avoid the warning
        states_filter = self._get_domain_states_filter(
            pholidays,
            start_dt,
            end_dt,
            partner_id=partner_id,
        )
        hhplo = self.env["hr.holidays.public.line"]
        holidays_lines = hhplo.search(states_filter)
        return holidays_lines

    @api.model
    def is_public_holiday(self, selected_date, employee_id=None, partner_id=None):
        """
        Override to avoid warning when both employee_id and partner_id are passed.
        Returns True if selected_date is a public holiday for the employee
        :param selected_date: datetime object
        :param employee_id: ID of the employee
        :param partner_id: ID of the partner
        :return: bool
        """
        partner = self._get_partner_deprecated_employee(
            partner_id, employee_id
        )
        partner_id = partner.id if partner else None
        # Only pass partner_id to avoid the warning
        holidays_lines = self.get_holidays_list(
            year=selected_date.year, partner_id=partner_id
        )
        if holidays_lines:
            hol_date = holidays_lines.filtered(
                lambda r: r.date == selected_date
            )
            if hol_date.ids:
                return True
        return False
