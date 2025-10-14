# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create to handle telework declarations when creating leaves.
        If a leave is created in 'validate' state, remove conflicting
        telework declarations.
        """
        leaves = super().create(vals_list)

        for leave in leaves:
            if leave.state == 'validate' and not leave.request_unit_half:
                leave._remove_conflicting_telework_declarations()

        return leaves

    def write(self, vals):
        """
        Override write to handle telework declarations when approving leaves.
        When a leave is approved, remove conflicting telework declarations.
        """
        result = super().write(vals)

        # Check if state changed to validate
        if vals.get('state') == 'validate':
            for leave in self:
                if not leave.request_unit_half:
                    leave._remove_conflicting_telework_declarations()

        return result

    def _remove_conflicting_telework_declarations(self):
        """
        Remove telework declarations that conflict with this leave.
        Only removes declarations for full-day leaves.
        """
        self.ensure_one()

        if not self.employee_id or self.request_unit_half:
            return

        TeleworkDay = self.env['hr.telework.day']

        # Get the date range of the leave
        leave_start = self.date_from.date()
        leave_end = self.date_to.date()

        # Search for telework declarations in this date range
        conflicting_declarations = TeleworkDay.search([
            ('employee_id', '=', self.employee_id.id),
            ('date', '>=', leave_start),
            ('date', '<=', leave_end),
        ])

        if conflicting_declarations:
            # Log the deletion in the leave
            deleted_count = len(conflicting_declarations)
            deleted_dates = ', '.join([
                fields.Date.to_string(d.date)
                for d in conflicting_declarations
            ])

            self.message_post(
                body=_(
                    'Automatically removed %d telework declaration(s) '
                    'for dates: %s'
                ) % (deleted_count, deleted_dates)
            )

            # Delete the conflicting declarations
            conflicting_declarations.unlink()

    def action_refuse(self):
        """
        Override action_refuse to log information.
        When a leave is refused, telework declarations remain unchanged.
        """
        return super().action_refuse()
