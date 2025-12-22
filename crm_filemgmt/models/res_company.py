# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = "res.company"

    # Company-dependent char stored via ir.property.
    file_prefix = fields.Char(
        help="Short prefix used when generating file codes. Max 10 characters.",
        company_dependent=True,
    )

    # Add a computed field that shows the prefix in uppercase
    file_prefix_upper = fields.Char(
        string="File Prefix (Upper Case)",
        compute="_compute_file_prefix_upper",
        store=False,
        help="File prefix converted to uppercase for display purposes.",
    )

    @api.constrains("file_prefix")
    def _check_file_prefix_allowed_chars(self):
        """Optionally restrict to alphanumeric characters."""
        for rec in self:
            if rec.file_prefix:
                # Check if contains only letters, numbers, and underscores
                import re

                if not re.match(r"^[A-Za-z0-9_]*$", rec.file_prefix):
                    raise ValidationError(
                        rec.env._(
                            "File Prefix can only contain letters, numbers, and underscores."
                        )
                    )

    @api.constrains("file_prefix")
    def _check_file_prefix_length(self):
        """Enforce a hard limit of 10 characters."""
        for rec in self:
            if rec.file_prefix and len(rec.file_prefix) > 10:
                raise ValidationError(
                    rec.env._("File Prefix must be at most 10 characters.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        """Trim whitespace before saving."""
        for vals in vals_list:
            if "file_prefix" in vals and vals["file_prefix"]:
                vals["file_prefix"] = vals["file_prefix"].strip()
        return super().create(vals_list)

    def write(self, vals):
        """Trim whitespace before saving."""
        if "file_prefix" in vals and vals["file_prefix"]:
            vals = dict(vals)
            vals["file_prefix"] = vals["file_prefix"].strip()
        return super().write(vals)
