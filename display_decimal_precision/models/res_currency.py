# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import math

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResCurrency(models.Model):
    _inherit = "res.currency"

    display_rounding = fields.Float(
        # string removed (redundant with field name)
        digits=(12, 6),
        help=(
            "Optional visual rounding. If set between 0 and 1 (e.g. 0.01), the UI "
            "will prefer that many decimal places for display. If empty or 0, the "
            "currency's own decimal places are used."
        ),
    )

    display_decimal_places = fields.Integer(
        compute="_compute_display_decimal_places",
        store=True,
        help=(
            "Derived number of decimals used for display: "
            "ceil(log10(1/display_rounding)) when 0 < display_rounding < 1; "
            "otherwise falls back to the currency's decimal_places "
            "(or 0 if rounding >= 1)."
        ),
    )

    @api.depends("rounding", "decimal_places", "display_rounding")
    def _compute_display_decimal_places(self):
        """Compute preferred display decimals based on custom display_rounding.

        Rules:
          - If display_rounding in (0, False): use native decimal_places.
          - If 0 < display_rounding < 1: ceil(log10(1 / display_rounding)).
          - Else (>=1): 0.
        """
        for currency in self:
            dr = currency.display_rounding
            if not dr:
                # Falls back to currency.decimal_places (native Odoo field)
                currency.display_decimal_places = int(currency.decimal_places or 0)
            elif 0 < dr < 1:
                # Guard against floating noise (e.g. 0.1000000000003)
                try:
                    # log10(1/x) -> number of decimals needed to represent x
                    val = 1.0 / float(dr)
                    # Safety clamp
                    if not math.isfinite(val) or val <= 0:
                        raise ValueError
                    decs = int(math.ceil(math.log10(val)))
                except (ValueError, TypeError, OverflowError):
                    # Fallback sane default if input weirdness occurs
                    decs = int(currency.decimal_places or 0)
                # Clamp to a reasonable UI range
                currency.display_decimal_places = max(0, min(12, decs))
            else:
                # dr >= 1 -> show as integer
                currency.display_decimal_places = 0

    # --- Validations & QoL ---

    @api.constrains("display_rounding")
    def _check_display_rounding(self):
        """Ensure non-negative and not subnormal values."""
        for currency in self:
            dr = currency.display_rounding
            if dr is None:
                continue
            if dr < 0:
                raise ValidationError(self.env._("Display Rounding must be >= 0."))
            # Prevent absurdly tiny values that explode decimals
            if 0 < dr < 10**-12:
                raise ValidationError(
                    self.env._("Display Rounding is too small. Use a value >= 1e-12.")
                )

    @api.onchange("display_rounding")
    def _onchange_display_rounding(self):
        if self.display_rounding and self.display_rounding < 0:
            return {
                "warning": {
                    "title": self.env._("Invalid value"),
                    "message": self.env._(
                        "Display Rounding must be a non-negative number."
                    ),
                }
            }
        return {}
