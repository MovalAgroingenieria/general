# 2026 Moval Agroingenieria
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    _ANALYTIC_ONLY_FIELDS = {
        "analytic_distribution",
        "analytic_account_id",
        "analytic_tag_ids",
    }

    def write(self, vals):
        changed_fields = set(vals.keys()) if vals else set()
        only_analytic_changes = (
            changed_fields and changed_fields.issubset(self._ANALYTIC_ONLY_FIELDS)
        )

        if only_analytic_changes:
            # pylint: disable=W0642
            self = self.with_context(_sii_only_analytic_change=True)

        return super().write(vals)
