# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def get_currencies(self):
        """Return currencies dict for the web client with adjusted display digits.

        In v18, `decimal.precision` is gone and currencies rely on their own
        decimal fields. We set the `digits` scale to the currency's preferred
        display scale:
          - use `display_decimal_places` if present,
          - otherwise fall back to `decimal_places`.
        """
        res = super().get_currencies()
        if not res:
            return res

        currency_model = self.env["res.currency"]
        # Only browse the currencies already returned by super (respect access rules)
        for currency in currency_model.browse(list(res.keys())):
            entry = res.get(currency.id)
            if not entry:
                continue

            # Prefer display_decimal_places when available; fallback to decimal_places
            scale = getattr(currency, "display_decimal_places", None)
            if scale is None:
                scale = getattr(currency, "decimal_places", 2) or 2

            # Keep the original total precision (first element) if present, else 16
            digits = entry.get("digits")
            total_precision = 16
            if isinstance(digits, (list, tuple)) and len(digits) == 2:
                total_precision = digits[0] or 16

            # Assign a JSON-serializable pair (list), not mutating in place
            entry["digits"] = [total_precision, int(scale)]

        return res
