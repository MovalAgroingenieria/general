# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class HrHolidaysPublic(models.Model):
    _inherit = 'hr.holidays.public'

    @api.model
    def is_public_holiday(self, selected_date, employee_id=None, partner_id=None):
        """
        Returns True if selected_date is a public holiday for the employee
        :param selected_date: datetime object
        :param employee_id: ID of the employee
        :param partner_id: ID of the partner
        :return: bool
        """
        # Avoid warning when both employee_id and partner_id are provided
        if employee_id and partner_id:
            employee_id = None
        partner = self._get_partner_deprecated_employee(partner_id, employee_id)
        partner_id = partner.id if partner else None
        holidays_lines = self.get_holidays_list(
            year=selected_date.year, partner_id=partner_id, employee_id=employee_id
        )
        if holidays_lines:
            hol_date = holidays_lines.filtered(lambda r: r.date == selected_date)
            if hol_date.ids:
                return True
        return False
