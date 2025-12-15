# 2023-2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, tools


class DecimalPrecision(models.Model):
    _inherit = 'decimal.precision'

    display_digits = fields.Integer(
        string='Display Digits',
        required=True, default=2)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "digits" in vals and "display_digits" not in vals:
                vals["display_digits"] = vals["digits"]
            vals.setdefault("display_digits", vals.get("digits", 2))
        return super().create(vals_list)

    @api.model
    def get_display_precision(self, application):
        icp = self.env["ir.config_parameter"].sudo()
        for key in (
                f"display_decimal_precision.dp.{application}",
                f"customer_purchase_follow_up.dp.{application}",  # legacy
        ):
            val = icp.get_param(key)
            if val not in (None, False, ""):
                try:
                    return (16, int(val))
                except (TypeError, ValueError):
                    pass

        # fallback a la tabla decimal_precision (si mantienes display_digits)
        self.env.cr.execute(
            "SELECT display_digits FROM decimal_precision WHERE name=%s",
            (application,),
        )
        row = self.env.cr.fetchone()
        return (16, row[0] if row and row[0] is not None else 2)
