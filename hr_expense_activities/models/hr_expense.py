# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import models
from odoo.tools.misc import (  # Casts "True"/"False" strings from ICP to booleans
    str2bool,
)


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    def action_submit_sheet(self):
        """
        Submit expense sheets with an optional bypass of activity creation.

        Behavior:
        - If system parameter 'hr_expense_activities.with_activity' is truthy,
          delegate to the native behavior (which may create activities, etc.).
        - Otherwise, directly move sheets from 'draft' to 'submit'
        without creating activities.

        Notes:
        - Supports multi-record sets.
        - Returns True or the result of super() for RPC consistency.
        """
        icp = self.env["ir.config_parameter"].sudo()
        with_activity = str2bool(
            icp.get_param("hr_expense_activities.with_activity", default="False")
            or "False"
        )

        if with_activity:
            # Use the standard Odoo flow (includes potential activity creation)
            return super().action_submit_sheet()

        # Bypass activities: only update records currently in 'draft'
        self.filtered(lambda s: s.state == "draft").write({"state": "submit"})
        return True
