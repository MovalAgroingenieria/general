# Copyright 2023-2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0.html).

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class DecimalPrecision(models.Model):
    """Add a display precision on top of the standard decimal precision model.

    Odoo uses ``decimal.precision.digits`` as the computation precision.
    This module introduces ``display_digits`` to format values with a different
    number of decimals than the computation precision.
    """

    _inherit = "decimal.precision"

    display_digits = fields.Integer(
        string="Display Digits",
        required=True,
        default=2,
        help="Number of decimal digits to use when formatting values.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Default display_digits to digits when not explicitly provided."""
        for vals in vals_list:
            if "digits" in vals and "display_digits" not in vals:
                vals["display_digits"] = vals["digits"]
            vals.setdefault("display_digits", vals.get("digits", 2))
        return super().create(vals_list)

    @api.model
    def get_display_precision(self, name):
        """Return the display precision tuple for a given decimal precision name.

        :param str name: decimal precision name (e.g. "Product Price")
        :return: (total_digits, decimal_digits)
        :rtype: tuple(int, int)
        """
        self.env.cr.execute(
            "SELECT display_digits FROM decimal_precision WHERE name = %s",
            (name,),
        )
        row = self.env.cr.fetchone()
        digits = row[0] if row and row[0] is not None else 2
        try:
            return (16, int(digits))
        except (TypeError, ValueError):
            _logger.warning(
                "Invalid display_digits for decimal precision %s: %r. Falling back to 2.",
                name,
                digits,
            )
            return (16, 2)
